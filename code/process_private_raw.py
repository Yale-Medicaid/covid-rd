import pandas as pd
import numpy as np
import snowflake.connector


def query_and_clean_mortality_data(user, account, warehouse, role):
    """
    Queries the mortality Database, de-duplicates records and creates basic values derived from 
    other data fields (indicators used in the regression discontinuity)

    Params
    ------
    user : string
        Username ending in @SHYFTANALYTICS.COM to connect to snowflake database
    account : string
        Account associated with the research project
    warehouse : string
        Mortality warehouse specific to research group, i.e. 'MORTALITY_00031_WH'
    role: string
        Role used to query database, i.e. MORTALITY_00031_ROLE

    Return
    ------
    pd.DataFrame
        DataFrame of mortality data aggregated to number of deaths for each time period by
        age in months. There are other slight modifications that need to be made before 
        exporting from the server. 
    """

    # Connect to DataBase. 
    ctx = snowflake.connector.connect(
            user=user,
            account=account,
            authenticator='externalbrowser',
            warehouse=warehouse,
            dbname='MORTALITY',
            schema='public')
    cs = ctx.cursor()
    cs.execute(f'use role {role}')
    cs.execute(f'use warehouse {warehouse}')


    selections = ['DATE_OF_DEATH', 'DATE_OF_BIRTH', 'GENDER', 'GENDER_PROBABILITY_SCORE']

    # Loop through relevant years and collect data
    l = []
    for year in range(2015, 2021):
        # Query DataBase for all deaths in the year
        cs.execute(f'select {", ".join(selections)} frin "MORTALITY"."PUBLIC".DEATH_INDEX"' 
                   + f" WHERE (DATE_OF_DEATH >= '{year}-01-01' AND DATE_OF_DEATH < '{year+1}-01-01')")

        # Put data in a DataFrame
        data = cs.fetchall()
        df = pd.DataFrame(data, columns=[x[0] for x in cs.description])
        df.columns = df.columns.str.lower()

        # Sanitize gender score and de-duplicate
        df['gender_probability_score'] = pd.to_numeric(df['gender_probability_score'])
        df = dedup_records(df)

        # Convert to `datetime64[ns]
        for col in ['date_of_birth', 'date_of_death']:
            df[col] = pd.to_datetime(df[col])

        df['age_in_mos'] = calc_age_in_mos(df)

        # Get # of deaths by month of death, age in months and gender
        df = (df.groupby(['date_of_death', 'age_in_mos', 'gender'], as_index=False).size()
                .rename(columns={'size': 'num_deaths'}))

        l.append(df)

    # Join data from all years
    df = pd.concat(l, ignore_index=True)

    # Reshape
    df = (df.pivot_table(index=['date_of_death', 'age_in_mos'],
                         columns='gender', values='num_deaths')
            .add_prefix('num_deaths_')
            .reset_index())

    # Total deaths across Male and Female
    df['num_deaths_tot'] = df[['num_deaths_F', 'num_deaths_M']].sum(1)

    # Create variables useful in the regression discontinuity
    df['ge65'] = df['age_in_mos'].ge(65*12).astype(int)
    df['age_in_mos_rel65'] = df['age_in_mos'] - 65*12
    df['age_in_years'] = df['age_in_mos']/12

    return df


def create_excess_deaths(df, outcome='num_deaths_tot'):
    	"""
    Transforms preliminary cleaned data from the mortality database into the analytic table
    of excess deaths for individuals 65-74 years old in 2020 relative to 2015-2019

    Params
    ------
    df : pd.DataFrame
        Output from query_and_clean_mortality_data
    outcome : str, default 'num_deaths_tot', {'num_deaths_tot', 'num_deaths_M', 'num_deaths_F'}
    	Specifies which grouping of deaths to consider and calculate excss deaths for

    Return
    ------
    pd.Series
        Series of excess deaths based on `outcome` for 2020 relative to 2015-2019.
        The output of this should be exported and saved and called 'excess_deaths_data.csv'
    """

    s = (df.groupby([df.date_of_death.dt.year.rename('year'),
                    df.date_of_death.dt.month.rename('month'), 
                    df['age_in_mos']])
            [outcome].sum())

    s2020 = s.xs(2020, level='year')
    s1519 = s.loc[[*range(2015, 2020)]]

    # Look for excess deahts among [65, 74)
    age_rng = (65, 74)

    # Subset ot age ranges and get total deaths per month of the year. 
    s2020 = s2020[(s2020.index.get_level_values('age_in_mos') >= age_rng[0]*12)
                   & (s2020.index.get_level_values('age_in_mos') < age_rng[1]*12)]
    s2020 = s2020.groupby(level='month').sum()

    s1519 = s1519[(s1519.index.get_level_values('age_in_mos') >= age_rng[0]*12)
                   & (s1519.index.get_level_values('age_in_mos') < age_rng[1]*12)]
    # Get total deaths, then divide by 5 to get average per year between 2015-2019
    s1519 = s1519.groupby(level='month').sum().div(5)

    # Create Excess Deaths. Set date to be the middle of the month.
    res = (s2020 - s1519).div(s1519).mul(100)
    res.index = pd.to_datetime([f'2020-{month}-15' for month in res.index])

    # Rename so saving as a csv has proper names
    res = res.rename_axis(index='date').rename('excess_deaths').reset_index()

    # Sorted so will align properly. 
    res['deaths_2020'] = s2020.to_numpy()
    res['deaths_1519'] = s1519.to_numpy()

    return res


def create_RD_table(df, outcome='num_deaths_tot'):
    """
    Transforms preliminary cleaned data from the mortality database into the analytic table
    for the regression discontinuity analysis

    Params
    ------
    df : pd.DataFrame
        Output from query_and_clean_mortality_data
    outcome : str, default 'num_deaths_tot', {'num_deaths_tot', 'num_deaths_M', 'num_deaths_F'}
    	Specifies which grouping of deaths to consider and calculate excss deaths for

    Return
    ------
    pd.DataFrame
        Analytic table for regression discontinuity
        The output of this should be exported and saved and called f'RD_data{outcome}.csv', so 
        if the outcome is 'num_deaths_tot' the file should be 'RD_data_num_deaths_tot.csv'.
    """

    # Holds aggregate data we need to export
    d_data {}

    # BWs for RD around age 65
    for age_rng in [(59, 71), (61, 69), (63, 67)]:

        # We need to compare March:Dec 2015-2019 with March:Dec 2020
        grpr = (df[(df.date_of_death.between('2015-01-01', '2019-12-31')
                    & df.date_of_death.dt.month.between(3, 12))
                   | df.date_of_death.between('2020-03-01', '2020-12-31')]
                  .groupby(df.date_of_death.dt.year.lt(2020)))

        for year, gp in grpr:
            # Transform label to more readable
            year = {True: '2015 - 2019', False: '2020'}.get(year)

            # Keep only ages in bandwidth and donut so exclude 65. 
            gp = gp[gp.age_in_mos.ge(age_rng[0]*12) & gp.age_in_mos.lt(age_rng[1](12))]
            gp = gp[~gp.age_in_mos_rel65.eq(0)]

            # Group to every 3 months for analytic table 
            gp = (gp.groupby(gp['age_in_mos']//3)
                    .agg({outcome: 'mean',
                          'ge65': 'first',
                          'age_in_mos_rel65': 'mean',
                          'age_in_years': 'mean'})
                    .reset_index())

            # Because we take the mean multiply by 3 for the collapsing of 3 months and by 10 
            # due to this being done over a 10 month period. 
            gp[outcome] = gp[outcome]*10*3

            d_data[(age_rng, year)] = gp

    df1 = pd.concat(d_data)
    df1 = df1.rename_axis(index=['age_rng', 'year', 'idx']).reset_index()

    return df1


#############
### Helper functions, not directly called
#############
 def calc_age_in_mos(df):
    """ 
    Vectorized, returns age in months

    Params
    ------
    df : pd.DataFrame
        DataFrame created from querying the Mortality DataBase

    Return
    ------
    pd.Series
        Series with the age in months for each row in the original DataFrame
    """

    yd = (df['date_of_death'].dt.year - df['date_of_birth'].dt.year)*12
    ms = (df['date_of_death'].dt.month - df['date_of_birth'].dt.month)

    return yd + ms


def dedup_records(df):
    """
    Because rows are duplicated with respect to gender, need to implement logic to de-duplicate.
    Keep all with probability > 0.5, then need to keep only half of the rows where the 
    probability is exactly 0.5

    Params
    ------
    df : pd.DataFrame
        DataFrame created from querying the Mortality DataBase

    Return
    ------
    pd.DataFrame
        DataFrame of exactly 1/2 the length where records have been de-duplcated with respect to
        gender
    """

    orig_len = len(df)

    keeps = df['gender_probability_score'].gt(0.5)

    # Keep half of the rows that are missing a probability or exactly equal to 0.5
    ids1 = (df[df['gender_probability_score'].isnull()]
              .groupby(['date_of_death', 'date_of_birth'])
              .sample(frace=0.5)
              .index)
    ids2 = (df[df['gender_probability_score'].eq(0.5)]
              .groupby(['date_of_death', 'date_of_birth'])
              .sample(frac=0.5)
              .index)

    df = df[keeps | df.index.isin(ids1) | df.index.isin(ids2)]
    fin_len = len(df2)

    # Sanity check that we have exactly 1/2 of the original rows, i.e. de-duplicated properly
    print(f'Original length: {orig_len:,}\nFinal length: {fin_len:,}\n{fin_len/orig_len}')

    return df