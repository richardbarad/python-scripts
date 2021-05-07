# -*- coding: utf-8 -*-
"""
This script is used to create graphics which are used as input to the Hot Spot Profile Analysis.
It creates graphics showing the HLPS for each livelihood zone in a country and also graphics showing the number of single shocks which result in IPC deficits in the zone.

The inputs to the script are:
    1) The two letter iso code for country (before running script, you must create a folder inside the HotSpot folder - folder name should be the two letter iso code for the country being analyzed.
    2) A file path to a folder containing the results (ress_summ.xlsx) files for you country of focus.
    3) A path the file containing global HLPS for all livelihood zones - this file is stored in the Hotspot profile folder on the Livelihoods Sharepoint.
    4) The number of rows included in the single shock analysis results summary files.

"""

import os
import pandas as pd
import matplotlib.pyplot as plt

params = {
        'country'             :'HT', #Two letter iso code for country.
        'single_shock_results':r'C:\Users\rbarad.CHEMONICS_HQ\Chemonics\Stephen Browne - Single shock Analyses\HT\Results', #Folder containing the single shock analysis results
        'HLPS_file'           :'HLPS.xlsx', #Excel file with global HLPS data
        'rows'                :64, #Number of rows in the Single Shock Analysis results
        }

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

#Clean up file and set index
data.sort_values(by='LZCODE',axis=0,inplace=True)
data.set_index('LZCODE',inplace=True)

#Calcualte the number of single shocks which results in deficits indicative of IPC Phase 2+ and 3+ in each zone.
columns= data.columns
IPC3_plus_col = [i for i in columns if i.endswith('P3plus')]
IPC2_plus_col = [i for i in columns if i.endswith('P2plus')]
data['3plus_count'] = (data[IPC3_plus_col] > 0).sum(axis=1)
data['2plus_count'] = (data[IPC2_plus_col] > 0).sum(axis=1)

#Change directory to country directory within the Hotspot profiles folder - files exported here.
os.chdir(os.path.join(os.getcwd(),params['country']))

#Exort results to CSV
print('Export Results to a csv')
data.to_csv('HLPS_single_shock.csv')
print('Script Complete')

#PLOT Single Shock information in graphs
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

#Plot HLPS information
data.plot(y='HLPS',kind='bar',rot=60)
plt.ylabel("Livelihood Protection Score (LPS)")
plt.title("Livelihood Protection Score (LPS) by Zone")
plt.tight_layout()
plt.ylim((1,data['HLPS'].max() + 0.05))
plt.savefig('HLPS.png')
plt.show()
