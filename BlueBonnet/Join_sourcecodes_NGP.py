# -*- coding: utf-8 -*-
"""
Created on Mon Jul  5 13:29:59 2021

@author: richa
"""

import pandas as pd
import os

pd.set_option('display.max_columns', 5)

os.chdir(r'..\..\data\processed\actblue_ngp')

actblue_csv = r'..\..\..\data\raw\actblue_ngp\kelly-fowler-48075-contributions-all.csv'
source_codes_tags_csv = r'..\..\..\data\raw\actblue_ngp\fundraiser_source_codes_tags.csv'
ngp_txt = r'..\..\..\data\raw\actblue_ngp\ContributionReport-19079884465.txt'

actblue_keep_fields = ['Receipt ID', 'Date','Amount','Fundraiser Recipient ID','Reference Code','Donor First Name','Donor Last Name']
ngp_keep_fields = ['Contribution ID','VANID','Contact Name','Amount','Source Code','Donor First Name','Donor Last Name','Date']

def read_clean_actblue_data():
    # Path to the actblue csv data
    actblue_df = pd.DataFrame(pd.read_csv(actblue_csv))  # Read data
    actblue_df = actblue_df[actblue_keep_fields]  # Select only key fields
    #Convert date to datetime instead of object
    actblue_df['Date'] = pd.to_datetime(actblue_df['Date'])
    actblue_df['Donor First Name'] = actblue_df['Donor First Name'].str.upper()
    actblue_df['Donor Last Name'] = actblue_df['Donor Last Name'].str.upper()
    #Filter to only include data from before January 2021
    actblue_df_filt =  actblue_df[actblue_df['Date'] < '2021-01-01']
    actblue_df_filt['Date'] = pd.to_datetime(actblue_df_filt['Date']).dt.date
    actblue_df_filt['Date'] = actblue_df_filt['Date'].astype(str)
    return actblue_df_filt

#Read in the source codes provided by campaign
source_codes_tags_df = pd.read_csv(source_codes_tags_csv)
source_codes_tags_df = source_codes_tags_df[['Fundraiser Recipient ID', 'Reference Code', 'Source Code', 'Tags']]


actblue_df = read_clean_actblue_data()

#Merge source does with processed actblue data
def merge_source_codes_actblue():
    actblue_df_sourcecodes = actblue_df.merge(source_codes_tags_df, how='left', on=['Fundraiser Recipient ID', 'Reference Code'])
    field_list = [f for f in list(actblue_df.columns) if f not in ['Donor Last Name','Date','Amount']]
    for field in field_list:
        new_field_name = field + '_actblue'
        actblue_df_sourcecodes.rename(columns={field:new_field_name},inplace=True)
    return actblue_df_sourcecodes

#Read and clean / process ngp data
def def_read_clean_ngp():
    ngp_df = pd.read_csv(ngp_txt, sep='\t', encoding='latin-1')
    new = ngp_df['Contact Name'].str.split(',', expand=True)
    ngp_df['Donor First Name'] = new[1].str.upper() #Make upper case
    ngp_df['Donor Last Name'] = new[0].str.upper() #Make upper case
    ngp_df['Date'] = pd.to_datetime(ngp_df['Date Received']) #Convert to date
    ngp_df.drop(ngp_df[ngp_df['Date'] >= pd.to_datetime('2021-01-01')].index, inplace=True) #Filter to only pre 2021 data
    ngp_df['Donor Last Name'] = ngp_df['Donor Last Name'].str.split(' ', expand=True)[0] #Get just first word of last name
    ngp_df= ngp_df[ngp_keep_fields] #Select only important fields
    ngp_df['Date'] = ngp_df['Date'].astype(str) #Convert date back to a string
    field_list_ngp = [f for f in list(ngp_df.columns) if f not in ['Donor Last Name','Date','Amount']] #Append '_ngp' to fileds not used in join
    for field in field_list_ngp:
        new_field_name = field + '_ngp'
        ngp_df.rename(columns={field:new_field_name},inplace=True)
    return ngp_df

clean_ngp_df = def_read_clean_ngp()
print(clean_ngp_df.info())

actblue_plus_sourcecode = merge_source_codes_actblue()
print(actblue_plus_sourcecode.info())

clean_ngp_df.to_excel('ngp_clean.xlsx',index=False,header=True)
actblue_plus_sourcecode.to_excel('actblue_with_source_codes_tags.xlsx',index=False, header=True)

#Join ngp data to actblue data
ngp_actblue_merge = clean_ngp_df.merge(actblue_plus_sourcecode,how='outer',on=['Amount','Donor Last Name', 'Date'],indicator=True)

#Filter tonly include merged entries where source code is ActBlue and ActbLue General
#also include rows where value is right_only as there have a null for the NGP Source code.
ngp_actblue_merge = ngp_actblue_merge[(ngp_actblue_merge['Source Code_ngp'] == 'ActBlue') | \
                                      (ngp_actblue_merge['Source Code_ngp'] == 'ActBlue General') | \
                                      (ngp_actblue_merge['_merge'] == 'right_only')]

ngp_actblue_merge.sort_values(by='Date',axis=0,inplace=True) #Sort by date

#Replace right only with NGP only and left only with ActBlue Only
ngp_actblue_merge['_merge'] = ngp_actblue_merge['_merge'].replace('right_only', 'ActBlue_only')    
ngp_actblue_merge['_merge'] = ngp_actblue_merge['_merge'].replace('left_only', 'NGP_only')    

print(ngp_actblue_merge.info())
ngp_actblue_merge.to_excel('ngp_actblue_merge.xlsx',index=False,header=True)
