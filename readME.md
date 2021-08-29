# covid-rd


Data replication ReadMe  for
*Association Between Medicare Eligibility and Excess Deaths From COVID-19 in the US*  
Jacob Wallace, Anthony Lollo, Chima Ndumele, JAMA Health Forum

## Replication Code
The programs for the main paper analyses are provide as `.py` files that need to be run in a python environment.

#### Required Packages and Versions
The analysis was performed with the following libraries and versions, so to ensure reproducibility packages and versions should match.

```
python 3.9.1

pandas 1.3.1
numpy 1.19.5
scipy 1.6.0
statsmodels 0.12.2
matplotlib 3.3.3
```

#### Data Sources
This paper primarily uses restricted mortality data provided by the [Covid-19 Research Database](https://covid19researchdatabase.org/).
These data may be obtained by registering with the research database and requesting access to the *Mortality Database*. The raw data must then be queried from their database.

We also use publicly available mortality data from the National Center for Health Statistics.
As these data are continually updated we have provided the file we used as of the time of publication within this replication package.
Updated versions of the [Weekly Counts of Deaths by Jurisdiction and Age](https://data.cdc.gov/NCHS/Weekly-Counts-of-Deaths-by-Jurisdiction-and-Age/y5bj-9g5w) are found through the link.

#### Raw Data

The publicly available data are provided and located in `data\raw\public\`.  

The private data are not provided and should be obtained by the replicator.
As these data are private and need to be disaggregated before exporting from the COVID-19 Research Database environment,
there will be no raw files for the private data. Instead, we have provided code that will allow the replicator to
carry out the same analysis within the COVID-19 Research Database environment and then the exported files should be placed in `data\processed\private\`

#### Analysis and Processing Scripts

All code for this project is provided within the `code\` folder.
Each file script should be run in the order it appears in this ReadMe, and we provide a basic description the inputs, outputs, and transformations for each script.

1. `process_public_raw.py`: Takes as input `'data\raw\public\Weekly_Counts_of_Deaths_by_Jurisdiction_and_Age.csv'`,
calculates the excess deaths for each 4-week period in 2020 as compared to 2015-2019 and outputs a simple Series to `'data\processed\public\NCHS_excess_deaths.pkl'`

2. `process_private_raw.py`: These steps must be performed within the COVID-19 Research Database. These steps query raw data from the Mortality Database and construct monthly counts of death, by age in years, for the 2015-2019 period and the 2020 period. When the output files are approved for export by the COVID-19 Research Database team, they can be placed in `data\processed\private\` so that the following analytic steps can proceed.  
  - First the replicator should run `query_and_clean_mortality_data` to query 2015-2020 data from the mortality Database, and perform basic data cleaning. The replicator will need to provide their own specific username, roles, and access codes specific to their project to be able to connect to the snowflake database.

  - Next the replicator will run `create_excess_deaths` which will transform the DataFrame from `query_and_clean_mortality_data` into a Series of excess deaths in 2020. For the main analysis, the outcome parameter should be set to `'num_deaths_tot'`, sensitivity analyses looking at splits by gender can change this to `'num_deaths_M'`', or `'num_deaths_F'`'.  The replicator should
  save the Series returned by this function as a comma delimited file named `'excess_death_data.txt'` then request to export this files out of the COVID-19 Research Database environment and can place it within the `data\processed\private\` folder to continue with the replication.

  - Next the replicator will run `create_RD_table` which will transform the DataFrame from `query_and_clean_mortality_data` into the analytic table required for the regression discontinuity analysis. For the main analysis, the outcome parameter should be set to `'num_deaths_tot'`, sensitivity analyses looking at splits by gender can change this to `'num_deaths_M'`, or `'num_deaths_F'`. The replicator should save the DataFrame returned by this function as a  pipe-delimited (`'|'`) file named `'RD_data_num_deaths_tot.txt'` and request to export this file out of the COVID-19 Research Database environment. This file should be placed within `data\processed\private` to continue with the replication.

3. `run_main_analyses.py`: Takes as input files from `data\processed\` and reproduces the main tables and estimates of the manuscript. Within this script are two functions, `create_excess_death_figure` will create the first figure of the manuscript and `create_rd_figure` will run the regression discontinuity specification and produce figure 2 of the manuscript. The figures will be output to `data\output\`. If the replicator seeks additional information regarding the RD estimates they should inspect `res.summary()`, the result of the RD model run within `create_rd_figure`.
