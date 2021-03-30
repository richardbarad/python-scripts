# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 11:54:01 2021

@author: rbarad
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import requests
import datetime

params = {
        'country'             :'HT',
        'ipc_analysis'        :'HT_IPC_Analysis_ML1.xlsx',
        'single_shock_results':r'C:\Users\rbarad.CHEMONICS_HQ\Chemonics\Stephen Browne - Single shock Analyses\Round 2 Single Shock\Haiti\Results',
        'HLPS_file'           :'HLPS.xlsx',
        'rows'                :64,
        'IPC_Analysis_type'   :'Admin1_LHZ' #Options are LHZ_Admin1 or LHZ
        }

if params['IPC_Analysis_type'] == 'LHZ_Admin1':
    ag_columns = ['ADMIN1','LZCODE']
elif params['IPC_Analysis_type'] == 'LHZ':
    ag_columns = ['LZCODE']

landscan_url=r'https://fdw.fews.net/api/geographicunit/?country=' + params['country'] + '&unit_type=fsc_admin_lhz&as_of_date=' + str(datetime.date.today()) + '&format=json&fields=with_population'
print(landscan_url)

#Read IPC Analysis data into a Dataframe
ipc_analysis = os.getcwd() + os.sep + 'IPC Analysis' + os.sep + params['country'] + os.sep + params['ipc_analysis']
ipc_df = pd.DataFrame(pd.read_excel(ipc_analysis))
ipc_df.set_index('FNID',inplace=True)

#Get population data from the FDW and join to IPC Data
print("Get landscan data from FDW API")
r = requests.get(landscan_url)
landscan = pd.read_json(r.text)
landscan.set_index('fnid',inplace=True)
ipc_df = ipc_df.merge(landscan[['estimated_population']],left_index=True,right_index=True) #Join to IPC Data

#Get Total LH/Admin 1 or LH Population and join back to IPC Dataframe, calculate percentage of total population at higher level unit for each mapping unit
print("Calculate the percent of population in each mapping unit, based on selected level of analysis")
admin2sum = ipc_df.groupby(ag_columns,as_index=False)[['estimated_population']].sum()
admin2sum.rename({'estimated_population':'lhz_pop'},axis=1,inplace=True)
ipc_df = ipc_df.merge(admin2sum,on=ag_columns)
ipc_df['pct'] = ipc_df['estimated_population'] / ipc_df['lhz_pop']

#Multiply IPC values by percentages, and sum together results of multiplication (this calculates a weigted average in which all admin units within an LH Zone are weighted based on thier population)
print("Calculate aggreagated Average IPC Phase and Percent of Cyles in IPC Phase 3 plus, apply weigted average")
ipc_df['ipc_avg_weight'] = ipc_df['IPC_avg'] * ipc_df['pct']
ipc_df['ipc_3plus_weight'] = ipc_df['IPC_3plus'] * ipc_df['pct']
ipc_df['ipc_2plus_weight'] = ipc_df['IPC_2plus'] * ipc_df['pct']

if params['IPC_Analysis_type'] == 'LHZ_Admin1':
    ipc_df['LHZ_Admin1'] = ipc_df['LZCODE'] + ' ' + ipc_df['ADMIN1']
    IPC_Agg_LHZ = ipc_df.groupby(['LHZ_Admin1'],as_index=False)[['ipc_avg_weight','ipc_3plus_weight','ipc_2plus_weight']].sum()
    IPC_Agg_LHZ.set_index('LHZ_Admin1',inplace=True)
    IPC_Agg_LHZ['ipc_3plus_weight']=IPC_Agg_LHZ['ipc_3plus_weight'] * 100
    IPC_Agg_LHZ['ipc_2plus_weight']=IPC_Agg_LHZ['ipc_2plus_weight'] * 100
elif params['IPC_Analysis_type'] == 'LHZ':
    IPC_Agg_LHZ = ipc_df.groupby(['LZCODE'],as_index=False)[['ipc_avg_weight','ipc_3plus_weight','ipc_2plus_weight']].sum()
    IPC_Agg_LHZ.set_index('LZCODE',inplace=True)
    IPC_Agg_LHZ['ipc_3plus_weight']=IPC_Agg_LHZ['ipc_3plus_weight'] * 100
    IPC_Agg_LHZ['ipc_2plus_weight']=IPC_Agg_LHZ['ipc_2plus_weight'] * 100

#Read HLPS data into a Dataframe and filter to country of focus
print ("Read HLPS Data")
hlps_df = pd.DataFrame(pd.read_excel(params['HLPS_file'])) #Read
data = hlps_df[hlps_df['COUNTRY'] == params['country']] #filter

#Create a list of results summary files - exclude drought and baseline scenarios
single_results = [i for i in os.listdir(params['single_shock_results']) if not i.endswith(('drought.xlsx','baseline.xlsx'))]

#Merge results of each single shock analysis into a pandas dataframe, and join to HLPS data creating a final dataframe with all shocks
for result in single_results:
    #Read data
    shock=result.split('_')[3][:-5]
    excel_file = params['single_shock_results'] + os.sep + result
    print('Processing data for ' + shock)
    df_name= "df_" + shock
    df_name = pd.DataFrame(pd.read_excel(excel_file,sheet_name='Phase_Dist_Annual',skiprows=3,usecols='D:E,G:L',nrows=params['rows']))
    #Clean Data
    column_list = df_name.columns
    df_name.rename({column_list[0]:'ADMIN1',column_list[1]:'Admin2_LHZ'},axis=1,inplace=True)
    df_name['ADMIN2']=df_name['Admin2_LHZ'].str.split('_').str[0]
    df_name['LZCODE']=df_name['Admin2_LHZ'].str.split('_').str[1]
    #Calculate IPC 3 plus pct, and IPC 2 plus pct for shock
    col_name3 = shock + '_P3plus'
    col_name2 = shock + '_P2plus'
    df_name[col_name3] = (df_name['Wor_P3'] + df_name['Wor_P4'] + df_name['Wor_P5']) / df_name['Wor_pop']
    df_name[col_name2] = (df_name['Wor_P2']+ df_name['Wor_P3'] + df_name['Wor_P4'] + df_name['Wor_P5']) / df_name['Wor_pop']
    #Drop columns
    drop_columns=['Admin2_LHZ','Wor_pop','Wor_P1','Wor_P2','Wor_P3','Wor_P4','Wor_P5']
    df_name.drop(drop_columns,axis=1,inplace=True)
    df_name.drop_duplicates(subset='LZCODE',inplace=True)
    #Join data to join dataframe and overwrite join dataframe
    data = data.merge(df_name[['LZCODE',col_name2,col_name3]],on='LZCODE',how='left')

data.set_index('LZCODE',inplace=True)
columns= data.columns
IPC3_plus_col = [i for i in columns if i.endswith('P3plus')]
IPC2_plus_col = [i for i in columns if i.endswith('P2plus')]
data['3plus_count'] = (data[IPC3_plus_col] > 0).sum(axis=1)
data['2plus_count'] = (data[IPC2_plus_col] > 0).sum(axis=1)

os.chdir(os.path.join(os.getcwd(),params['country']))

#Plot IPC Results
print('Plot IPC Results')
plt.rcParams["figure.figsize"] = [9,6]

IPC_Agg_LHZ.plot(y='ipc_3plus_weight',kind='bar',rot=-80)
plt.ylabel("Percent in IPC 3 plus")
plt.title("Average Percent of Cycles in IPC Phase 3+")
plt.tight_layout()
plt.savefig('IPC_3plus.png')
plt.show()

IPC_Agg_LHZ.plot(y='ipc_avg_weight',kind='bar',rot=-80)
plt.ylabel("IPC Area Phase")
plt.ylim((1,IPC_Agg_LHZ['ipc_avg_weight'].max()+0.2))
plt.title("Average IPC Area Phase")
plt.tight_layout()
plt.savefig('IPC_Av.png')
plt.show()

#Exort results to CSV
print('Export Results to a csv')
IPC_Agg_LHZ.to_csv('IPC_aggregated.csv')
data.to_csv('HLPS_single_shock.csv')
print('Script Complete')

#PLOT Single Shock
print('Plot Single Shock and HLPS')
plt.rcParams["figure.figsize"] = [6,4]

data.plot(y='3plus_count',kind='bar',rot=60)
plt.ylabel("Number of Shocks with Deficits")
plt.title("Number of Shocks Resulting in Deficits Indicative of IPC Phase 3+")
plt.yticks(range(data['3plus_count'].max()+ 2))
plt.tight_layout()
plt.savefig('Single_Shock_3plus.png')
plt.show()

data.plot(y='2plus_count',kind='bar',rot=60)
plt.ylabel("Number of Shocks with Deficits")
plt.title("Number of Shocks Resulting in Deficits Indicative of IPC Phase 2+")
plt.yticks(range(data['2plus_count'].max()+ 2))
plt.tight_layout()
plt.savefig('Single_Shock_2plus.png')
plt.show()

data.plot(y='HLPS',kind='bar',rot=60)
plt.ylabel("Livelihood Protection Score (LPS)")
plt.title("Livelihood Protection Score (LPS) by Zone")
plt.tight_layout()
plt.ylim((1,data['HLPS'].max() + 0.05))
plt.savefig('HLPS.png')
plt.show()
