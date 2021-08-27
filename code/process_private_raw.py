import pandas as pd
import numpy as np
import snowflake.connector


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
    		schema='public'
    	)
    cs = ctx.cursor()
    cs.execute(f'use role {role}')
    cs.execute(f'use warehouse {warehouse}')


    selections = ['DATE_OF_DEATH', 'DATE_OF_BIRTH', 'GENDER', 'GENDER_PROBABILITY_SCORE']

    # Loop through relevant years and collect data
    l = []
    for year in range(2015, 2021):
    	# Query DataBase for all deaths in the year
    	cs.execute(f'select {", ".join(selections)} frin "MORTALITY"."PUBLIC".DEATH_INDEX"' 
    			   + f" WHERE (DATE_OF_DEATH >= '{year}-01-01' AND DATE_OF_DEATH < '{year+1}-01-01')"
    			  )

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


 def create_RD_datasets(df):
 	"""
	Transforms preliminary cleaned data from the mortality database into analytic tables used
	in the Regression Discontinuity analysis. 
 	"""