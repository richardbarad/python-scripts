# -*- coding: utf-8 -*-
"""
Created on Tue Jun  1 10:25:18 2021

@author: rbarad
"""

import requests
import pandas as pd
from matplotlib import pyplot as plt

crop_data=r'C:\Users\rbarad\Chemonics\FEWS NET Technical Team - 08.Analysis_tools\Hotspot\MG\MG24\Crop Production\MG_Ag_production_Addtional_data.xlsx'

#Get MG Crop Production Data from FDW

crop_url=r'https://fdw.fews.net/api/cropproductionfacts/?format=json&country_code=MG&cpcv2=R01122&cpcv2=R01592&indicator=crop:quantity&fields=simple'
print("Get MG crop data from FDW API")
r = requests.get(crop_url, verify=False)
print('Read data into df')
crop_df = pd.read_json(r.text)
crop_df = crop_df[['country','admin_0','admin_1','admin_2','admin_3','value','season_year','season_date','product']]
crop_df['year'] = crop_df['season_year'].str[-4:].astype(int)

#Filter data
print("Filter Data")
crop_df_filt = crop_df[crop_df['admin_2'] == 'Androy']
crop_df_pivot = crop_df_filt.pivot_table(values='value',index='year',columns='product',aggfunc='sum') #Pivot data
crop_filter = crop_df_pivot.loc['2000':] #Filter to only include data after 2000

years_list = crop_filter.index.tolist()

#Calc Problem specs
cassava_baseline = crop_filter.loc[2017,'Cassava']
maize_baseline = crop_filter.loc[2017,'Maize (Corn)']
crop_filter['cassava_ps'] = crop_filter['Cassava'] / cassava_baseline * 100
crop_filter['maize_ps'] = crop_filter['Maize (Corn)'] / maize_baseline * 100

crop_filter.to_csv('Androy_production.csv')

print(crop_filter)

#Make chart for Cassava

fig, ax = plt.subplots()
ax.bar(crop_filter.index,crop_filter['Cassava'],width=0.4,color='red')
ax.set_xticks(years_list)
plt.xticks(rotation=90)
ax.set_xlabel("Année")
ax.set_ylabel("Tonnes métriques")
plt.show()

#Make chart for Maize

fig, ax = plt.subplots()
ax.bar(crop_filter.index,crop_filter['Maize (Corn)'],width=0.4,color='blue')
ax.set_xticks(years_list)
plt.xticks(rotation=90)
ax.set_xlabel("Année")
ax.set_ylabel("Tonnes métriques")
plt.show()