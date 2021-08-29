import pandas as pd
import numpy as np 
import matplotlib.pyplot as plt
import os
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches

from statsmodels.formula.api import ols


def create_excess_death_figure():
	"""
	Create Figure 1 of manuscript illustrating excess deaths in 2020 relative to 2015-2019 and
	using COVID-19 Research Database and NCHS Data
	"""

	directory = (((os.path.dirname(os.path.dirname(os.path.realpath(__file__)))).replace('\\', '/')) 
				  + '/')

	dfnchs = pd.read_pickle(directory+'data/processed/public/NCHS_excess_deaths.pkl')
	dfdata = pd.read_csv(directory+'data/processed/private/excess_death_data.txt')

	# Since was exported to .txt need to re-cast to datetime. 
	dfdata['date'] = pd.to_datetime(dfdata['date'])

	fig,ax = plt.subplots(figsize=(8, 6))
	dfdata.plot(x='date', y='excess_deaths', label='Datavant', ax=ax, lw=2)
	dfnchs.plot(x='date', y='excess_deaths', label='National Center for\nHealth Statistics',
	            ax=ax, lw=2)

	ax.tick_params(which='major', labelsize=11)
	ax.set_xlim('2020-01', '2020-12-31')
	ax.set_ylim(-10,60)

	ax.set_xlabel(None)
	ax.set_ylabel('Excess deaths, %', fontsize=12)

	ax.axhline(0, 0, 1, color='black', lw=1.3)

	# Change tick labels to Month abbreviations. 
	ticks_loc = ax.get_xticks().tolist()
	ax.xaxis.set_major_locator(mticker.FixedLocator(ticks_loc))
	ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 
						'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
	                   rotation=0, ha='center')
	plt.legend()
	plt.tight_layout()
	plt.savefig(directory+'data/output/excess_deaths.png', dpi=300)
	plt.show()


def create_rd_figure(outcome='num_deaths_tot', bw='(61, 69)'):
	"""
	Create Figure 2 of manuscript showing the RD estimate for the main specification used in the 
	manuscript. The outcome can be changed to deaths for men and women if those outcomes were also
	created within the COVID-19 Research Database

	Params
	------
	outcome : str, default 'num_deaths_tot', {'num_deaths_tot', 'num_deaths_M', 'num_deaths_F'}
		Specifies which grouping of deaths to consider and calculate excss deaths for
	bw : str, default '(61, 69)', {'(59, 71)', '(61, 69)', '(63, 67)'}
	    Specifies the bandwidth around 65 to use for the RD estimates. 
	"""

	directory = (((os.path.dirname(os.path.dirname(os.path.realpath(__file__)))).replace('\\', '/')) 
				  + '/')

	df = pd.read_csv(directory+f'data/processed/private/RD_data_{outcome}.txt', sep='|')

	# Main specification used 61-69 bandwidth
	df = df[df.age_rng.eq(bw)]

	# Plotting colors and text locations. 
	cd = {'2020': '#1f77b4', '2015 - 2019': '#ff7f0e'}
	sd = {'2020': {'x': 61, 'y': 9300}, '2015 - 2019': {'x': 66.1, 'y': 6900}}


	fig,ax = plt.subplots(figsize=(8, 6))
	ax.tick_params(which='major', labelsize=11)

	for year in ['2020', '2015 - 2019']:
	    gp  = df[df.year.eq(year)]
	    gp.plot(x='age_in_years', y='num_deaths_tot', 
	            lw=0, marker='o', ax=ax, ms=2.5, label=year, color=cd[year])
	    
	    # Diff-in-Diff with quadratic 
	    mod = ols(formula=('num_deaths_tot ~ age_in_mos_rel65 + ge65 + age_in_mos_rel65 * ge65'
	                       ' + np.power(age_in_mos_rel65, 2) + np.power(age_in_mos_rel65, 2) * ge65'),
	              data=gp)

	    # Looking at `res.summary()` will show full regression table. 
	    res = mod.fit(cov_type='HC1', use_t=True)
	    
	    # For plotting each side of the RD separately
	    lw = np.linspace(-4, 0, 200)
	    up = np.linspace(0, 4, 200)
	          
	    # Plot <65
	    ax.plot(lw+65, (res.params['Intercept'] 
	                    + lw*12*res.params['age_in_mos_rel65']
	                    + (lw*12)**2*res.params['np.power(age_in_mos_rel65, 2)']),
	            color=cd[year], lw=1.5)
	    # Plot >65
	    ax.plot(up+65, (res.params['Intercept'] 
	                    + up*12*res.params['age_in_mos_rel65']
	                    + (up*12)**2*res.params['np.power(age_in_mos_rel65, 2)']
	                    + res.params['ge65'] 
	                    + up*12*res.params['age_in_mos_rel65:ge65']
	                    + (up*12)**2*res.params['np.power(age_in_mos_rel65, 2):ge65']),
	            color=cd[year], lw=1.5)
	 
	    # Label of RD estimate and 95% CI to add to plot
	    s = (res.params['ge65'].round(1).astype(str) + ' (95% CI: '
	         + res.conf_int().loc['ge65'].round(1).astype(str).str.cat(sep=', ') + ')')
	    ax.text(s=f'Change at 65 ({year}):\n {s}', **sd[year],
	            fontsize=11.5, color=cd[year])
	    
	# Add arrow artists to plot 
	style="Simple,tail_width=0.4,head_width=6,head_length=8"
	kw = dict(arrowstyle=style, color='#1f77b4', lw=1.2)
	a1 = mpatches.FancyArrowPatch((64.1, 9500), (64.9, 9260), **kw, zorder=20)
	plt.gca().add_patch(a1)   

	style="Simple,tail_width=0.4,head_width=6,head_length=8"
	kw = dict(arrowstyle=style, color='#ff7f0e', lw=1.5)
	a1 = mpatches.FancyArrowPatch((66, 7000), (65.1, 7300), **kw, zorder=20)
	plt.gca().add_patch(a1)   

	ax.axvline(65,0,1, color='black', lw=1.2, linestyle='--')

	ax.set_ylabel('Death count, No.', fontsize=12)
	ax.set_xlabel('Age, years', fontsize=12, labelpad=9)

	plt.legend(fontsize=11)
	plt.tight_layout()
	plt.savefig(directory+'data/output/RD_figure.png', dpi=300)
	plt.show()


if __name__ == '__main__':
    create_excess_death_figure()
    create_rd_figure()