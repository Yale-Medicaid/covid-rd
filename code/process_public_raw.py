import pandas as pd
import numpy as np 
import os


def clean_raw_NCHS_data():
    """
    Transform table of raw weekly death counts by jurisdiction to a ratio of death counts between
    2020 and 2015-2019 by week of the year.  
    """

    directory = (((os.path.dirname(os.path.dirname(os.path.realpath(__file__)))).replace('\\', '/')) 
                 + '/')
    file = 'Weekly_Counts_of_Deaths_by_Jurisdiction_and_Age.csv'

    df = pd.read_csv(directory+'data/raw/public/'+file)

    # Weekly counts of deaths by age group and time period for each week 
    s = (df[df.Type.eq('Unweighted') & df['Jurisdiction'].eq('United States')]
           .groupby(['Time Period', 'Week', 'Age Group'])['Number of Deaths'].mean())

    # To best-match CODID-19 Database, which is at the month level group every 4 weeks (~month) 
    s = s.groupby(['Time Period', (s.index.get_level_values('Week')-1)//4, 'Age Group']).sum()

    # Calculate % of Excess Deaths relative to 2015-2019 
    s1 = ((s.xs('2020') - s.xs('2015-2019', level=0))
            .div(s.xs('2015-2019', level=0)).mul(100)
            .xs('65-74 years', level=1)
            .rename('excess_deaths'))

    # Make the index dates. As NCHS uses `Week Ending Date`, we should set the date of the 4 week
    # periods to the `Week Ending Date` of the 2nd row in each 4 week period, i.e. the middle.
    dates = (df[df.Type.eq('Unweighted') & df['Jurisdiction'].eq('United States') 
                & df['Time Period'].eq('2020')]
               .groupby((df['Week']-1)//4)['Week Ending Date'].nth(1))

    dates = pd.to_datetime(dates).rename('date')
    s1.index = dates
    s1 = s1.reset_index()

    # Sorted so will align
    s1['deaths_2020'] = s.xs('2020').xs('65-74 years', level=1).to_numpy()
    s1['deaths_1519'] = s.xs('2015-2019').xs('65-74 years', level=1)

    # 2020 has 53 weeks so we compare the 52 weeks in 2015-2019 with the 52 weeks in 2020
    s1 = s1[:13]
    s1 = s1.reset_index()

    s1.to_pickle(directory+'data/processed/public/NCHS_excess_deaths.pkl')


if __name__ == '__main__':
    clean_raw_NCHS_data()