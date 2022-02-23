# -*- coding: utf-8 -*-
"""
Created on Mon Sep  6 15:37:12 2021

@author: richa
"""

import os
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib import dates as mdates
import numpy as np
import datetime

os.chdir(r'..\..\data\processed\ngp_analysis')

ngp_excel = r'..\..\raw\ngp\ngp_all_3.xlsx'

end_date = '2021-10-01'

ngp_excel_df = pd.read_excel(ngp_excel)

# ACCES GOOGLE SHEET

source_code_group_url = 'https://docs.google.com/spreadsheets/d/1-aMlLj5F7NQQsxybPNbCIkjWeVi2gWQMNV_Z8OeDtxU/gviz/tq?tqx=out:csv&sheet=Sheet1'
source_code_group = pd.read_csv(source_code_group_url)

#Clean data, create generlized type column by combining information from multiple columns
ngp_excel_df.loc[ngp_excel_df['Contribution ID'] == 2589300,'Source Code'] = 'Party'
ngp_excel_df.loc[ngp_excel_df['Contribution ID'] == 2589300,'Source Code Path'] = 'Organizations/Party'
ngp_excel_df = ngp_excel_df[ngp_excel_df['Date Received'] < end_date]
ngp_excel_df['type'] = np.nan
ngp_excel_df.loc[ngp_excel_df['Payment Method'] == 'Cash','type'] = 'Cash'
ngp_excel_df.loc[ngp_excel_df['Payment Method'] == 'In-Kind','type'] = 'In-Kind'
ngp_excel_df.loc[ngp_excel_df['Contribution Type'] == 'In-kind Contribution','type'] = 'In-Kind'
ngp_excel_df = ngp_excel_df.merge(source_code_group, how='left',on=['Source Code','Source Code Path'])

ngp_excel_df['type'].fillna(ngp_excel_df['Source_Code_Gen'], inplace=True)
ngp_excel_df['type'].fillna('Other or Unkown', inplace=True)
ngp_excel_df['year'] = pd.DatetimeIndex(ngp_excel_df['Date Received']).year
ngp_excel_df['month'] = pd.DatetimeIndex(ngp_excel_df['Date Received']).month
ngp_excel_df.to_excel('ngp_data_class.xlsx')

types = ngp_excel_df['type'].unique()

years = [2017,2019,2021]

#Create Scatter Plots

type_max = ngp_excel_df.groupby('type')['Amount'].max()

for year in years:
    ngp_year_filt = ngp_excel_df[ngp_excel_df['year'] == year]
    year_min = datetime.datetime(year,1,1)
    year_max = datetime.datetime(year,12,1)
    os.chdir(r'..\..\..\reports\figures\ngp')
    for t in types:
        ngp_filt = ngp_year_filt[ngp_year_filt['type'] == t]    
        fig, ax = plt.subplots()
        ax.scatter(ngp_filt['Date Received'],ngp_filt['Amount'],s=1.5)
        ax.grid(axis='y',linewidth=0.5)
        ax.set_ylabel("Amount Donated (USD)")
        ax.set_xlabel("Date")
        ax.set_xlim([year_min, year_max])
        y_max = type_max.loc[t] + (type_max.loc[t] / 10)
        ax.set_ylim([0, y_max])
        fig_name = str(year) + t + '_scatter.png'
        plt.title("Donations from " + t + " in " + str(year))
        plt.xticks(rotation = 90)
        plt.savefig(fig_name, bbox_inches="tight")
        plt.show()

#Get aggregate statistics by year and month

os.chdir(r'..\..\..\data\processed\ngp_analysis')
df_agg = ngp_excel_df.groupby(['year','month','type'],as_index=False)['Amount'].agg(['sum','count','mean'])
df_agg.reset_index(inplace=True)
df_agg['day'] = 1
df_agg['date'] = pd.to_datetime(df_agg[['year','month','day']])
df_agg.to_excel('donation_summary.xlsx')

#Function to create chart showing donation count and sum by month for specific data
def create_count_sum_chart(df,sum_field,count_field,t):
    fig, ax1 = plt.subplots()
    ax1.plot(df.index,df[sum_field],alpha=0.5)
    ax1.grid(axis='y',linewidth=0.5)
    ax1.set_ylabel("Amounted Recieved Per Month",color='blue')
    ax1.set_xlabel("Month")
    ax1.set_ylim(bottom=0)
    ax2 = ax1.twinx()
    ax2.plot(df.index,df[count_field],color='red', alpha=0.5)
    ax2.set_ylim(bottom=0)
    ax2.set_ylabel("Number of Donations per month",color='red')
    one_month = mdates.MonthLocator(interval=1)
    ax1.tick_params(axis='y', colors='blue')
    ax2.tick_params(axis='y', colors='red')
    ax1.xaxis.set_minor_locator(one_month)
    three_month = mdates.MonthLocator(interval=3)
    ax1.xaxis.set_major_locator(three_month)
    ax1.set_xticklabels(ax.get_xticks(), rotation = 90)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig_name = t + '_sumandcountpermonth.png'
    plt.title("Number of Donations from " + t)
    plt.savefig(fig_name, bbox_inches="tight")
    plt.show()

#Function to create chart showing donation count by month for specific data
def create_sum_chart(df,field,title):
    fig, ax = plt.subplots()
    ax.plot(df.index,df[field])
    ax.grid(axis='y',linewidth=0.5)
    ax.set_ylabel("Amounted Recieved Per Month")
    ax.set_xlabel("Month")
    ax.set_ylim(bottom=0)
    one_month = mdates.MonthLocator(interval=1)
    ax.xaxis.set_minor_locator(one_month)
    three_month = mdates.MonthLocator(interval=3)
    ax.xaxis.set_major_locator(three_month)
    fig_name = field + '_totalpermonth.png'
    plt.title("Total Amount Donated from " + title)
    plt.xticks(rotation = 90)
    plt.savefig(fig_name, bbox_inches="tight")
    plt.show()

#Function to create chart showing donation sum by month for specific data
def create_count_chart(df,field,title):
    fig, ax = plt.subplots()
    ax.plot(df.index,df[field])
    ax.set_ylabel("Number of Donations per month")
    ax.grid(axis='y',linewidth=0.5)
    ax.set_xlabel("Month")
    ax.set_ylim(bottom=0)
    one_month = mdates.MonthLocator(interval=1)
    ax.xaxis.set_minor_locator(one_month)
    three_month = mdates.MonthLocator(interval=3)
    ax.xaxis.set_major_locator(three_month)
    fig_name = field + '_countpermonth.png'
    plt.title("Number of Donations per month from " + title)
    plt.xticks(rotation = 90)
    plt.savefig(fig_name, bbox_inches="tight")
    plt.show()

#Pivot data, seperate columns for each type of donation
df_agg_pivot = df_agg.pivot_table(index='date',columns='type',values=['count','sum'])
df_agg_pivot.fillna(0,inplace=True)
df_agg_pivot.columns = ['_'.join(x) for x in df_agg_pivot.columns]
count_list = []
sum_list= []

os.chdir(r'..\..\..\reports\figures\ngp')

for t in types:
    sum_field = 'sum_' + t
    count_field = 'count_' + t
    create_sum_chart(df_agg_pivot,sum_field,t)
    create_count_chart(df_agg_pivot,count_field,t)
    create_count_sum_chart(df_agg_pivot,sum_field,count_field,t)

for t in types:
    count_list.append('count_' + t)
    sum_list.append('sum_' + t)

df_agg_pivot['Total_Cash_onhand'] = (df_agg_pivot[sum_list].sum(axis=1)) - df_agg_pivot['sum_In-Kind']
df_agg_pivot['Count_Cash_Donation'] = (df_agg_pivot[count_list].sum(axis=1)) - df_agg_pivot['count_In-Kind']

create_sum_chart(df_agg_pivot,'Total_Cash_onhand','All Monetary Contributions')
create_count_chart(df_agg_pivot,'Count_Cash_Donation','All Monetary Contributions')
create_count_sum_chart(df_agg_pivot,'Total_Cash_onhand','Count_Cash_Donation','All Monetary Contributions')


df_agg_cash_only = df_agg[df_agg['type'] != 'In-Kind']
df_agg_date_filt = df_agg_cash_only[df_agg_cash_only['year'].isin([2017,2019,2021])]
df_agg_pivot2 = df_agg_date_filt.pivot_table(index='month',columns='year',values='sum',aggfunc='sum')
df_agg_pivot2.loc[1,2017] = 0
df_agg_pivot2.loc[2,2021] = 0
df_agg_pivot2.loc[2,2019] = 0
print(df_agg_pivot2)

fig, ax = plt.subplots()
ax.plot(df_agg_pivot2.index,df_agg_pivot2[2017],label='2017', alpha=0.5)
ax.plot(df_agg_pivot2.index,df_agg_pivot2[2019],label='2019', alpha=0.5)
ax.plot(df_agg_pivot2.index,df_agg_pivot2[2021],label='2021', alpha=0.5)
ax.set_xticks(np.arange(1,13))
ax.set_xticklabels(['Jan', 'Feb','Mar.','Apr.','May','Jun.','Jul.','Aug.','Sep.','.Oct','.Nov','.Dec'])
ax.set_ylabel("Total Cash Contributions")
ax.grid(axis='y',linewidth=0.5)
plt.title('$ Contributions by Month for 2017, 2019, 2021 Election Cycles')
ax.set_xlabel("Month")
plt.legend()
plt.savefig('election_comparison.png', bbox_inches="tight")
plt.show()