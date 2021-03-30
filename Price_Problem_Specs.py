# -*- coding: utf-8 -*-
"""
Created on Thu Mar 18 15:46:38 2021

@author: rbarad
"""


import pandas as pd
import requests
import matplotlib.pyplot as plt
import numpy as np
import datetime

params = {'fdw_dataset':'1753',
          'consumption_start':7,
          'baseline_year':'2013-2014',
          'date_range': [2010,2020]}

class get_process_data():
    def get_data(): #Get data from FDW based on FDW dataset
        print("Get the Price Data for Haiti from the FDW API") 
        url = 'https://fdw.fews.net/api/marketpricefacts/?format=json&dataset=' + params['fdw_dataset']  
        r = requests.get(url)
        prices = pd.read_json(r.text)
        return prices
    def calc_consumption_year(): #Clean data, calculate consumption year associated with each month and write consumption year to a new column. Use start month specificed in params
        print("Calculating Consumption Year")
        df_prices = get_process_data.get_data()   
        df_prices = df_prices[['country','market','product','product_source','start_date','value','currency','source_document']]
        df_prices['month'] = pd.DatetimeIndex(df_prices['start_date']).month
        df_prices['year'] = pd.DatetimeIndex(df_prices['start_date']).year
        df_prices.loc[(df_prices['month']<params['consumption_start']),'consumption_year'] = (df_prices['year'] - 1).astype(str) + '-' + df_prices['year'].astype(str)
        df_prices.loc[(df_prices['month']>=params['consumption_start']),'consumption_year'] = df_prices['year'].astype(str) + '-' + (df_prices['year'] + 1).astype(str)
        return df_prices
    def filter_data(): #Filter the data based on the date range specified in the params 
        print('Filter data')
        df_prices = get_process_data.calc_consumption_year() 
        min_date = datetime.date(params['date_range'][0],params['consumption_start'],1).strftime("%Y-%m-%d")
        max_date = datetime.date(params['date_range'][1],params['consumption_start'],1).strftime("%Y-%m-%d")
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
        columns = prices_pivot.columns.tolist() #Get list of columns to use as items to plot in graph
        #Next nine lines ensure that the first month of conusmption year is allways labeled, and label format is MM-YYYY
        year_range = range(params['date_range'][0],params['date_range'][1] + 1)
        label_list = []
        x = -11 
        label_spot = []
        for y in year_range:
            label = datetime.date(9999,params['consumption_start'],1).strftime("%m-") + str(y)
            label_list.append(label)
            x = x + 12 
            label_spot.append(x)
        #Plot graph
        plt.rcParams["figure.figsize"] = (10,5.4) 
        prices_pivot.plot(kind='line',y=columns,label=columns,rot=-70)
        plt.xticks(label_spot,labels=label_list)
        plt.ylabel("Price (" + currency +")")
        plt.xlabel("Date")
        plt.show()
    def price_by_consumption_year_chart():
        print('Create Price by Consumption Year Chart')
        columns = prices_agg.columns.tolist() #Get list of columns to use as items to plot in graph
        ref_years = prices_agg.index.tolist() #Get list of reference year - used to force every reference year to be labeled.
        years = len(ref_years) 
        plt.rcParams["figure.figsize"] = (5.2,4.3)
        #Plot Graph
        prices_agg.plot(kind='line',y=columns,label=columns,rot=-70)
        plt.xticks(np.arange(years),labels=ref_years)
        plt.ylabel("Price (" + currency +")")
        plt.xlabel("Consumption Year")
        plt.show()
    def problem_specs_counsumption_year_chart():
        print('Create Problem Specification Chart')
        columns_ps = [c for c in prices_agg_ps_df.columns.tolist() if c.endswith('_PS')] #Get list of columns which end in _PS
        ref_years = prices_agg_ps_df.index.tolist()
        years = len(ref_years)
        prices_agg.plot(kind='line',y=columns_ps,label=columns_ps,rot=-70)
        plt.xticks(np.arange(years),labels=ref_years)
        plt.ylabel("% Change from Reference Year")
        plt.xlabel("Consumption Year")        
        plt.show()

#Get and clean / process price data and make chart showing prices by month    
prices = get_process_data.filter_data()

currency = prices.loc[0,'currency']

make_charts.price_by_month_chart()

#Get average price across each consumption year and make a chart
prices_agg = aggregate_consumption_year()
make_charts.price_by_consumption_year_chart()
prices_agg.loc['2013-2014','Rice (Tchako)'] = 135 #Set reference year value for rice to 135 since there is no data for rice in Haiti - 135 based on trends
make_charts.price_by_consumption_year_chart()

#Calculate problem specs and make a chart showing problem specs
prices_agg_ps_df = calc_prob_specs()
make_charts.problem_specs_counsumption_year_chart()

#Export to a csv
prices_agg_ps_df.to_csv('price_ps.csv')
