# -*- coding: utf-8 -*-
"""
Created on Thu Mar 18 15:46:38 2021

@author: rbarad
"""

import os
import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import numpy as np
import datetime

os.chdir(r'C:\Users\rbarad\OneDrive - Chemonics\Desktop\example')

params = {'fdw_dataset':'1786',
          'consumption_start':4, #Indicate the month which is the consumption year start month (1-12)
          'baseline_year':'2017-2018', #Specificy the baseline year for the zone
          'date_range': [2001,2021], #Specify the range of data to use for the analysis - range must include basline year
          'months':[1,2,3,4,5,6,7,8,9,10,11,12], #Select the months to include the average price for each consumption year.
          'price_type':'StapleFood'} 

min_date = datetime.date(params['date_range'][0],params['consumption_start'],1).strftime("%Y-%m-%d")
max_date = datetime.date(params['date_range'][1],params['consumption_start'],1).strftime("%Y-%m-%d")

class get_process_data():
    def get_data(): #Get data from FDW based on FDW dataset
        print("Get the Price Data from the FDW API") 
        url = 'https://fdw.fews.net/api/marketpricefacts/?format=json&dataset=' + params['fdw_dataset']  
        r = requests.get(url,verify=False)
        print(r)
        prices = pd.read_json(r.text)
        return prices
    def calc_consumption_year(): #Clean data, calculate consumption year associated with each month and write consumption year to a new column. Use start month specificed in params
        df_prices = get_process_data.get_data()
        print("Calculating Consumption Year")
        df_prices = df_prices[['country','market','product','product_source','start_date','value','currency','source_document']]
        df_prices['start_date'] = pd.to_datetime(df_prices['start_date']) #Convert start date to date
        df_prices['month'] = df_prices['start_date'].dt.month
        df_prices['year'] = df_prices['start_date'].dt.year
        print(df_prices.info())
        df_prices.loc[(df_prices['month']<params['consumption_start']),'consumption_year'] = (df_prices['year'] - 1).astype(str) + '-' + df_prices['year'].astype(str)
        df_prices.loc[(df_prices['month']>=params['consumption_start']),'consumption_year'] = df_prices['year'].astype(str) + '-' + (df_prices['year'] + 1).astype(str)
        return df_prices
    def filter_data(): #Filter the data based on the date range specified in the params 
        df_prices = get_process_data.calc_consumption_year()
        print('Filter data')
        query = 'start_date >="' + min_date + '" and start_date <"' + max_date + '"'
        df_prices = df_prices.query(query)
        df_prices.reset_index(inplace=True,drop=True)
        return df_prices
    
def aggregate_consumption_year(): #Aggregate the data by calcuating the average price for each product by consumtion year
    print('Aggregate data by consumption year')
    prices_agg = pd.pivot_table(prices,index='consumption_year',columns='product',values='value',aggfunc='mean')
    return prices_agg

def calc_prob_specs(): #Calculate the problem specifications for each year and product (i.e: year / baseline year)
    print('Calculate Problem Specifications')
    columns_ps = []
    for column in prices_agg:
        prices_agg[column + '_PS'] = (prices_agg[column] / prices_agg.loc[params['baseline_year'],column]) * 100
        columns_ps.append(column + '_PS')
    return prices_agg
        
class make_charts(): #Make charts
    def price_by_month_chart(): #Make chart showing price in each month.
        print('Create Price by Month Chart')
        prices_pivot = pd.pivot_table(prices,index='start_date',columns='product',values='value') #Pivot data to format which allows for chart creation
        #Ensure there is a row for every month - if no data for specific months add a no data
        dates = pd.date_range(min_date, max_date, freq='MS')
        date_fill = prices_pivot.reindex(dates, fill_value=np.nan)
        columns = date_fill.columns.tolist() #Get list of columns to use as items to plot in graph
        #Plot graph 
        plt.rcParams["figure.figsize"] = (10,5.4) 
        fig, ax = plt.subplots()
        for column in columns:
            ax.plot(date_fill.index,date_fill[column],label=column)
        fmt_year = mdates.MonthLocator(interval=12)
        ax.xaxis.set_major_locator(fmt_year)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%Y'))
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter('{x:,.0f}'))
        ax.set_ylabel("Price (" + currency +")")
        ax.set_xlabel("Date")
        ax.grid(axis = 'x')
        ax.legend()
        fig.tight_layout()
        month_figname = params['price_type'] + '_month.png'
        plt.savefig(month_figname)
        plt.show()
    def price_by_consumption_year_chart():
        print('Create Price by Consumption Year Chart')
        columns = prices_agg.columns.tolist() #Get list of columns to use as items to plot in graph
        plt.rcParams["figure.figsize"] = (5.2,4.3)
        #Plot Graph
        fig, ax = plt.subplots()
        for column in columns:
            ax.plot(prices_agg.index,prices_agg[column],label=column)
        #ax.set_ylim(175,2600) #Adjust or remove as needed to ensure there is space for the legend
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter('{x:,.0f}'))
        ax.set_ylabel("Price (" + currency +")")
        ax.set_xlabel("Conusmption Year")
        ax.grid(axis = 'x')
        ax.tick_params(axis='x', labelrotation = -70)
        ax.legend()
        fig.tight_layout()
        year_figname = params['price_type'] + '_year.png'
        plt.savefig(year_figname)
        plt.show()
    def problem_specs_counsumption_year_chart():
        print('Create Problem Specification Chart')
        columns_ps = [c for c in prices_agg_ps_df.columns.tolist() if c.endswith('_PS')] #Get list of columns which end in _PS
        ref_years = prices_agg_ps_df.index.tolist()
        years = len(ref_years)
        prices_agg.plot(kind='line',y=columns_ps,label=columns_ps,rot=-70)
        plt.xticks(np.arange(years),labels=ref_years)
        #plt.ylim(65,350) #Adjust as needed to ensure there is space for the legend
        plt.ylabel("% Change from Reference Year")
        plt.legend(loc='best')
        plt.xlabel("Consumption Year")   
        plt.tight_layout()
        ps_figname = params['price_type'] + '_ps.png'
        plt.savefig(ps_figname)
        plt.show()

#Get and clean / process price data and make chart showing prices by month    
prices = get_process_data.filter_data()

currency = prices.loc[0,'currency']
make_charts.price_by_month_chart()

#Get average price across each consumption year and make a chart
prices = prices[prices['month'].isin(params['months'])]
prices_agg = aggregate_consumption_year()
make_charts.price_by_consumption_year_chart()

#Calculate problem specs and make a chart showing problem specs
prices_agg_ps_df = calc_prob_specs()
make_charts.problem_specs_counsumption_year_chart()

#Export to a csv
outputfile_name = params['price_type'] + '_price_PS.csv'
prices_agg_ps_df.to_csv(outputfile_name)
