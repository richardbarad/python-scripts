# -*- coding: utf-8 -*-
"""
Created on Tue Nov  2 13:57:27 2021

@author: rbarad
"""

import pandas as pd
import os
import arcpy
import arcgis
import sys
import xlsxwriter

pd.options.mode.chained_assignment = None  # default='warn'

wrsi_folder = sys.argv[1]
year_folder = sys.argv[2]
month_folder = sys.argv[3]
arcpy.env.workspace = os.path.join(wrsi_folder,'GDHI_Admin_Units.gdb')

fc_list = arcpy.ListFeatureClasses()
fc_list.remove('EA_GDHI_Admin_Units')

WRSI_data = {}

def get_product(product):
    if product == 'ee':
        full_product = 'MaizeL'
    elif product == 'el':
        full_product = 'GrainsL'
    elif product == 'ek':
        full_product = 'GrainsB'
    elif product == 'e2':
        full_product = 'RangeL'
    elif product == 'e1':
        full_product = 'RangeS'
    elif product == 'et':
        full_product = 'MaizeS'
    return full_product

def get_wrsi_data():
    print('Read WRSI Data')
    WRSI_data = {}
    for fc in fc_list:    
        fc_path = os.path.join(arcpy.env.workspace,fc)
        sdf = pd.DataFrame.spatial.from_featureclass(fc_path)
        sdf.set_index('FNID',inplace=True)
        sdf.drop(['SHAPE'],inplace=True,axis=1)
        for col in ['WRSI_2020','WRSI_2021','WRSI_2022','WRSI_2023','WRSI_2024','WRSI_2025']:
            sdf[col] = sdf[col].astype(float)
        product = fc[-2:]
        full_product = get_product(product)
        WRSI_data[full_product] = sdf
    return WRSI_data

WRSI_data = get_wrsi_data()

#Excel Files to import
et_crop_prod = r'.\05.WRSI\Crop Production Data\ET_agprod_data.xlsx'

#Array of new zones created from 2003 - Present, first item in dictionary is new zone and second item is zone which new zone used to be part of
changed_admin = {'Argoba':'South Wollo','Southeast Tigray':'South Tigray','Pawe':'Metekel',\
                 'West Omo':'Bench Maji','Gofa':'Gamo Gofa','Gamo':'Gamo Gofa','Alle':'Derashe','West Guji':'Borena',\
                 'Buno Bedele':'Ilubabor','Dire Dawa rural':'Dire Dawa','West Gondar':'North Gondar','Central Gondar':'North Gondar'}
    
class et_crop_data():
    def read_crop_data():
        print ("Read ET Crop Data")
        et_crop_df = pd.read_excel(et_crop_prod) #Read Data
        et_crop_df = et_crop_df[['country','fnid','country_code','admin_0','admin_1','admin_2','value','product','season_name','season_year']]
        et_crop_df['year'] = et_crop_df['season_year'].str[-4:].astype(int)
        et_crop_df.rename({'admin_1':'ADMIN1','admin_2':'ADMIN2','year':'YEAR','season_name':'SEASON','product':'PRODUCT'},axis=1,inplace=True)
        return et_crop_df
        
    def clean_data():
        #This functions cleans the ET Crop production data, mainly by filtering out uneeded data, and data points which we do not use in the GDHI.
        et_crop_raw = et_crop_data.read_crop_data()
        print ("Clean Data")
        et_crop_raw['PRODUCT'].replace({'Mixed Teff':'Teff','Maize (Corn)':'Maize','Wheat Grain':'Wheat'},inplace=True)
        #Remove admin1 units which are not needed in GDHI - Afar and Somali are in GDHI but we do not use crop production stats, just WRSI
        et_crop_filt1 = et_crop_raw[~et_crop_raw['ADMIN1'].isin(['Afar','Somali'])]         
        #These administrative units split into smaller zones, and crop production data for them is not comparable to data in newer units. 
        #They only report for one or two years since 2001 so do not lose much data by dropping
        et_crop_filt2 = et_crop_filt1[~et_crop_filt1['ADMIN2'].isin(['Keficho Shekicho','Kembata Alaba Tembaro','North Omo'])]
        #Set Admin 2 column to Admin1 unit name in Gambela, units in Gambela have changed over time so aggregate to Admin1 to get comparable time series
        et_crop_filt2.loc[(et_crop_filt2['ADMIN1'] == 'Gambela') & (et_crop_filt2['SEASON'] == 'Meher'),'ADMIN2'] = 'Gambela'
        et_crop_filt3 = et_crop_filt2[et_crop_filt2['YEAR'] > 2000] #Only include data from after 2000
        et_crop_filt4 = et_crop_filt3[~(et_crop_filt3['value'].isna())] #Remove rows with no crop production data
        et_crop_filt5 = et_crop_filt4[~((et_crop_filt4['ADMIN2'] == 'Bale') & (et_crop_filt4['PRODUCT'] == 'Sorghum') & (et_crop_filt4['YEAR'] < 2008))] #Drop Sorghum data for Bale, from before 2008. Values are low and significant outliers.
        print ("Update Admin Names")
        #Put data into a common unit, rename new admin units created after 2003 to the name of admin unit they were previously part of in 2003 map - names to change referenced in dictionary
        et_crop_filt5['ADMIN2'].replace(changed_admin,inplace=True)
        return et_crop_filt5
        
    def aggregate_data():
        #Function to aggregate data, data aggregated back into a common unit, based on ADMIN2 Name column in which names were revised above.
        et_crop_clean = et_crop_data.clean_data()
        et_crop_agg = et_crop_clean.groupby(['ADMIN1','ADMIN2','PRODUCT','SEASON','YEAR'],as_index=False,dropna=False)['value'].sum()
        return et_crop_agg

et_crop_data = et_crop_data.aggregate_data()

def calc_min_max():
    #Get min and max crop production for each admin 2 unit
    print("Calculate min / max production by zone")
    et_min_max = et_crop_data.groupby(['ADMIN1','ADMIN2','PRODUCT','SEASON'],as_index=False,dropna=False)['value'].agg(['min','max','count']) # Get min, max, mean, and count of crop production data points for each unit.
    et_min_max.reset_index(inplace=True)
    et_min_max['diff'] = et_min_max['max'] - et_min_max['min'] #Calc difference between min and max
    et_min_max = et_min_max[et_min_max['count'] > 4] #figure out which series have more than four datapoints, and delete ones which do not 
    et_min_max.drop('count',inplace=True,axis=1) #Drop the count, which is not needed
    et_min_max_pivot = et_min_max.pivot(index=['ADMIN1','ADMIN2','SEASON'],columns='PRODUCT',values=['min','max','diff']) #pivot data so that there is a min, max, diff column for each crop
    et_min_max_pivot.columns = ['_'.join(col).strip() for col in et_min_max_pivot.columns.values] #Strip column names so that they are a strings instead of tuple
    et_min_max_pivot.reset_index(inplace=True)
    et_min_max_pivot.rename({'ADMIN2':'ADMIN2_CROP'},inplace=True,axis=1)
    return et_min_max_pivot

et_crop_stats = calc_min_max()

#There are three different rainy season patterns in Ethiopia, which each follow different rainy season patterns. 
#These lists, list out the admin units (Admin2s / Admin3s) which are part of each pattern in cases where the whole Region (Admin1) does not follow the same pattern

somali_sap = ['Jarar','Erer','Korahe','Shebelle','Dollo','Afder','Liben','Nogob','Daawa'] #Southern Pastoral Zones (Admin2s) in Somali region
somali_nap = ['Sitti'] #Nothern pastoral Zones (Admin 2s) in Somali region

#Fanfan zone (Admin2) in Somali region includes both south and north pastoral woredas (Admin3)
fafan_nap= ['Gursum','Babile','Shabeeley','Aw-Bare','Kebribeyah','Tuliguled','Jigjiga City','Wajale City','Kebribayah Town','Haroreys','Harawo'] #Northern pastoral units in Fafan
fafan_sap= ['Harshin','Goljano','Koran/Mulla'] #Southern pastoral units in Fafan

oromia_sap = ['Borena'] #Southern agropastoral Admin2 (Zones) in Oromia. 
oromia_ag = ['West Wellega','East Wellega','Ilubabor','Jimma','West Shewa','North Shewa','East Shewa','Arsi',\
             'West Hararge','East Hararge','Bale','South West Shewa','Buno Bedele','West Arsi','Kelem','Horo Guduru','Finfinne'] #Agriculture Admin2 (Zones) in Oromia

#West Guji / Guji Zones in Oromia contain woredas (Admin3) which follow Southern Agropastoral and Agriculture pattern. Woredas are groupped into SAP and AG here.
gujii_sap = ['Adola','Wadera','Odo Shakiso','Liben','Saba Boru','Gora Dola','Negele Town','Aga Wayu','Adola Town','Gumi Idalo','Shakiso Town',\
           'Bule Hora','Kercha','Dugda Dawa','Melka Soda','Bule Hora Town','Suro Berguda','Birbirsa Kojowa']
gujii_ag = ['Uraga','Bore','Afele Kola','Girja','Ana Sora','Haro Walabu','Hambela Wamena','Abaya','Gelana'] 


def filter_data(df,region): #Function which filters WRSI data based on Southern Agropastoral, Northern Agropastoral, or Agriculture Areas
    if region == 'SAP':
        df_filt = df[(df['ADMIN2'].isin(somali_sap)) | ((df['ADMIN2'] == 'Fafan') & (df['ADMIN3'].isin(fafan_sap))) | (df['ADMIN2'].isin(oromia_sap)) | \
                     ((df['ADMIN2'].isin(['Gujii','West Guji'])) & (df['ADMIN3'].isin(gujii_sap)))]
    if region == 'NAP':
        df_filt = df[(df['ADMIN1'] == 'Afar') | (df['ADMIN2'] == 'Sitti') | ((df['ADMIN2'] == 'Fafan') & (df['ADMIN3'].isin(fafan_nap)))]
    if region == 'AG':
        df_filt = df[(df['ADMIN1'].isin(['Tigray','SNNPR','Amhara','Dire Dawa','Harari','Gambela','Benshangul Gumuz','Addis Ababa'])) \
                     | ((df['ADMIN1'] == 'Oromia') & (df['ADMIN2'].isin(oromia_ag))) | ((df['ADMIN2'].isin(['Gujii','West Guji'])) & (df['ADMIN3'].isin(gujii_ag)))]
    return df_filt

def get_wrsi_product(season,region,crop): #Function to select the appropriate WRSI product based on region (AG, NAP, or SAP), crop, and season.
    if season == 'Meher' and region == 'SAP':
        return 'RangeS'
    if season == 'Belg' and region in ('NAP','SAP'):
        return 'RangeL'
    if season == 'Meher' and region in ('NAP','AG') and crop =='Maize':
        return 'MaizeL'
    if season == 'Meher' and region in ('NAP','AG') and crop !='Maize':
        return 'GrainsL'
    if season == 'Belg' and region in ('AG'):
        return 'GrainsB'

class prod_calc():
    def merge(df_list):
        cols_to_use = df_list[0].columns.difference(df_list[1].columns) #This is so that output does not include columns present in both dfs
        mergeddf = df_list[1].merge(df_list[0][cols_to_use],left_index=True,right_index=True)
        return mergeddf
    
    def crop_calc(df,year,crop,season): #Function to calculate WRSI based crop production estimate using min/max production for a given year, crop, and season
        cropmin = 'min_' + crop 
        cropdiff = 'diff_' + crop 
        wrsi_crop_est = df[cropmin] + df[cropdiff] * (df[year] - 50) / 50 #Apply linear scalling formula
        wrsi_crop_est.loc[df[year] <= 50] = df[cropmin] #If less than 50 set to minimum production
        if season == 'Belg':
            wrsi_crop_est.loc[df['ADMIN1'] == 'Tigray'] = df[year] #For Belg season set values to WRSI value for Tigray - production series to short for linear scalling
        wrsi_crop_est.loc[df['ADMIN1'].isin(['Afar','Somali'])] = df[year] #For Afar & Somali region just set crop prod estimate to WRSI values, since not enough production data
        return wrsi_crop_est
    
    def get_data(region):
        #Function which accepts the name of a region (SAP, NAP, or AG) and returns a dictionary with the Belg and Meher WRSI based crop production estimates.
        ag_wrsi = {}
        print ("Get WRSI data for " + region)
        for season in ['Meher','Belg']:
            wrsi_ag_data_list = []
            et_crop_filt = et_crop_stats[et_crop_stats['SEASON'] == season] #Filter crop produciton data to just season of interest
            for crop in ['Maize','Grains']:
                product = get_wrsi_product(season,region,crop)
                wrsi_ag_df = WRSI_data[product]
                #Select WRSI data for admin zones which follow rainfall pattern of interest using a function
                wrsi_ag_filt = filter_data(wrsi_ag_df,region)
                wrsi_ag_filt.loc[:,'REGION'] = region #Add region column, and set to AG for agriculture
                wrsi_ag_filt.reset_index(inplace=True)
                if season == 'Meher':
                    wrsi_ag_filt.loc[:,'ADMIN2_CROP'] = wrsi_ag_filt['ADMIN2'] #Add new column with Admin2 names for joining to crop production data
                    wrsi_ag_filt['ADMIN2_CROP'].replace(changed_admin,inplace=True) #Update Admin2 names in new column, if unit used be part of another admin 2 unit - use dictionary to update.
                    #Set Admin 2 column to Admin1 unit name in Gambela, units in Gambela have changed over time so aggregate to Admin1 to get comparable time series for production
                    wrsi_ag_filt.loc[wrsi_ag_filt['ADMIN1'] == 'Gambela','ADMIN2_CROP'] = 'Gambela'
                    wrsi_prod_merge = wrsi_ag_filt.merge(et_crop_filt,on=['ADMIN1','ADMIN2_CROP'],how='left') #Join min / max production data, join on Admin2 for Meher
                if season == 'Belg':
                    wrsi_prod_merge = wrsi_ag_filt.merge(et_crop_filt,on=['ADMIN1'],how='left') #Join min / max prod data, join on Admin1 for Belg, Belg data only at Admin1 level
                print('Analysis for ' + region + ' ' + season + ' ' + crop)
                for year in range (2001,2026):
                    if crop == 'Maize':
                        new_field = crop + '_p' + str(year)
                        wrsi_col = 'WRSI_' + str(year)
                        wrsi_prod_merge[new_field] = prod_calc.crop_calc(wrsi_prod_merge,wrsi_col,crop,season)
                        wrsi_prod_merge.drop(wrsi_col,inplace=True,axis=1)
                    else:
                        for c in ['Sorghum','Wheat','Teff']:
                            new_field = c + '_p' + str(year)
                            wrsi_col = 'WRSI_' + str(year)
                            wrsi_prod_merge[new_field] = prod_calc.crop_calc(wrsi_prod_merge,wrsi_col,c,season)
                        wrsi_prod_merge.drop(wrsi_col,inplace=True,axis=1)
                wrsi_prod_merge.drop(['ADMIN2_CROP','SEASON','min_Maize','min_Sorghum','min_Teff','min_Wheat','diff_Maize','diff_Sorghum','diff_Teff','diff_Wheat'],inplace=True,axis=1)
                wrsi_ag_data_list.append(wrsi_prod_merge)
            ag_wrsi[season]= prod_calc.merge(wrsi_ag_data_list)
        return ag_wrsi
          
nap = prod_calc.get_data('NAP')
ag = prod_calc.get_data('AG')
sap = prod_calc.get_data('SAP')

#This part of the script merges together the results for the three geographic areas, reorders data, implements fallback logic and calculates average production for each crop.

#List of column names in correct, final order
col_ord_final = ['COUNTRY','ADMIN0','ADMIN1','ADMIN2','ADMIN3','PCODE','REGION','Maize_p2001','Sorghum_p2001','Wheat_p2001','Teff_p2001','Maize_p2002','Sorghum_p2002','Wheat_p2002','Teff_p2002', \
                 'Maize_p2003','Sorghum_p2003','Wheat_p2003','Teff_p2003','Maize_p2004','Sorghum_p2004','Wheat_p2004','Teff_p2004','Maize_p2005','Sorghum_p2005','Wheat_p2005','Teff_p2005', \
                 'Maize_p2006','Sorghum_p2006','Wheat_p2006','Teff_p2006','Maize_p2007','Sorghum_p2007','Wheat_p2007','Teff_p2007','Maize_p2008','Sorghum_p2008','Wheat_p2008','Teff_p2008', \
                 'Maize_p2009','Sorghum_p2009','Wheat_p2009','Teff_p2009','Maize_p2010','Sorghum_p2010','Wheat_p2010','Teff_p2010','Maize_p2011','Sorghum_p2011','Wheat_p2011','Teff_p2011', \
                 'Maize_p2012','Sorghum_p2012','Wheat_p2012','Teff_p2012','Maize_p2013','Sorghum_p2013','Wheat_p2013','Teff_p2013','Maize_p2014','Sorghum_p2014','Wheat_p2014','Teff_p2014',\
                 'Maize_p2015','Sorghum_p2015','Wheat_p2015','Teff_p2015','Maize_p2016','Sorghum_p2016','Wheat_p2016','Teff_p2016','Maize_p2017','Sorghum_p2017','Wheat_p2017','Teff_p2017',\
                 'Maize_p2018','Sorghum_p2018','Wheat_p2018','Teff_p2018','Maize_p2019','Sorghum_p2019','Wheat_p2019','Teff_p2019','Maize_p2020','Sorghum_p2020','Wheat_p2020','Teff_p2020', \
                 'Maize_p2021','Sorghum_p2021','Wheat_p2021','Teff_p2021','Maize_p2022','Sorghum_p2022','Wheat_p2022','Teff_p2022','Maize_p2023','Sorghum_p2023','Wheat_p2023','Teff_p2023', \
                 'Maize_p2024','Sorghum_p2024','Wheat_p2024','Teff_p2024','Maize_p2025','Sorghum_p2025','Wheat_p2025','Teff_p2025']

def merge_results(season):
    print('Merge results for ' + season + ' season')
    df_list = [nap[season],sap[season],ag[season]]
    results = pd.concat(df_list,ignore_index=True)
    return results
    
def calc_average(df): #Function to calcuate average crop production values
    print('Calculate Average Crop Production Values')
    df['Maize_pAV'] = df[['Maize_p2001','Maize_p2002','Maize_p2003','Maize_p2004','Maize_p2005','Maize_p2006','Maize_p2007','Maize_p2008','Maize_p2009','Maize_p2010','Maize_p2011','Maize_p2012', 
      'Maize_p2013','Maize_p2014','Maize_p2015','Maize_p2016','Maize_p2017','Maize_p2018','Maize_p2019','Maize_p2020']].mean(axis=1)
    df['Sorghum_pAV'] = df[['Sorghum_p2001','Sorghum_p2002','Sorghum_p2003','Sorghum_p2004','Sorghum_p2005','Sorghum_p2006','Sorghum_p2007','Sorghum_p2008','Sorghum_p2009','Sorghum_p2010','Sorghum_p2011','Sorghum_p2012', 
      'Sorghum_p2013','Sorghum_p2014','Sorghum_p2015','Sorghum_p2016','Sorghum_p2017','Sorghum_p2018','Sorghum_p2019','Sorghum_p2020']].mean(axis=1)
    df['Wheat_pAV'] = df[['Wheat_p2001','Wheat_p2002','Wheat_p2003','Wheat_p2004','Wheat_p2005','Wheat_p2006','Wheat_p2007','Wheat_p2008','Wheat_p2009','Wheat_p2010','Wheat_p2011','Wheat_p2012', 
      'Wheat_p2013','Wheat_p2014','Wheat_p2015','Wheat_p2016','Wheat_p2017','Wheat_p2018','Wheat_p2019','Wheat_p2020']].mean(axis=1)
    df['Teff_pAV'] = df[['Teff_p2001','Teff_p2002','Teff_p2003','Teff_p2004','Teff_p2005','Teff_p2006','Teff_p2007','Teff_p2008','Teff_p2009','Teff_p2010','Teff_p2011','Teff_p2012', 
      'Teff_p2013','Teff_p2014','Teff_p2015','Teff_p2016','Teff_p2017','Teff_p2018','Teff_p2019','Teff_p2020']].mean(axis=1)
    return df

def fallback_logic(df,season):
    print('Implement fallback logic to fill data gaps for ' + season + ' season')
    year_columns = ['AV'] + list(range(2001,2026))
    for year in year_columns:
        maize_col = 'Maize_p' + str(year)
        sorghum_col = 'Sorghum_p' + str(year)
        wheat_col = 'Wheat_p' + str(year)
        teff_col = 'Teff_p' + str(year)
        df[teff_col] = df[teff_col].fillna(df[wheat_col]) #If Teff data not available, set to Wheat
        df[teff_col] = df[teff_col].fillna(df[sorghum_col]) #If Teff and Wheat not available, set Teff to Sorghum value
        df[teff_col] = df[teff_col].fillna(df[maize_col]) #If Teff, Wheat, and Sorghum not available, set Teff value to Maize
        df[wheat_col] = df[wheat_col].fillna(df[sorghum_col]) #If Wheat value not avaialble, set Wheat to Sorghum
        df[wheat_col] = df[wheat_col].fillna(df[maize_col]) #If Wheat and Sorghm not available, set Wheat to Maize
        df[sorghum_col] = df[sorghum_col].fillna(df[maize_col]) #If Sorghum not available, set Sorghum to Maize
        df[sorghum_col] = df[sorghum_col].fillna(df[wheat_col]) #If Sorghum and Maize not wavailable, set Sorghum to Wheat
        df[maize_col] = df[maize_col].fillna(df[sorghum_col]) #if Maize not available, set Maize value to Sorghum
        df[maize_col] = df[maize_col].fillna(df[wheat_col]) #If Maize and Sorghum not available, set Maize value to Wheat
        #Implement fall back logic for current season, set to average in geographic areas where season has not started. When analysis occurs mid season WRSI will not have started yet in some areas.
        if month_folder in ['1','2']: #If January or February then in short rains season, rainy season year will be previous year.
            rains_year = int(year_folder) - 1
        else:
            rains_year = int(year_folder)
        if rains_year == year: #For current season implement fall back logic
            print('Set Crop Production estimate to Long Term Average in areas where season has not started yet for ' + season + ' season')
            df[teff_col] = df[teff_col].fillna(df['Teff_pAV']) #If Teff data is not avaialble for current season set to average, data might not be available when season has not started yet in an area.
            df[wheat_col] = df[wheat_col].fillna(df['Wheat_pAV']) #If Wheat data is not avaialble for current season set to average, data might not be available when season has not started yet in an area.
            df[maize_col] = df[maize_col].fillna(df['Maize_pAV']) #If Maize data is not avaialble for current season set to average, data might not be available when season has not started yet in an area.
            df[sorghum_col] = df[sorghum_col].fillna(df['Sorghum_pAV']) #If Sorghum data is not avaialble for current season set to average, data might not be available when season has not started yet in an area.        
    return df

os.chdir(os.path.join(wrsi_folder,year_folder,month_folder)) #Move to folder where results should be exported

meher_results = merge_results('Meher') #Merge results for Meher season
meher_results.sort_values('FNID',axis=0,inplace=True) #Sort based on FNID
meher_results.set_index('FNID',inplace=True) #Set index to FNID
meher_results = meher_results[col_ord_final] #Set column order to order needed for GDHI - order specified in col_ord_final list.
meher_results = calc_average(meher_results)
meher_results_f = fallback_logic(meher_results,'Meher') #Implement fall back logic function
print('Export results for the Meher to Excel')
writer = pd.ExcelWriter('ET_Meher_results.xlsx',engine='xlsxwriter')
meher_results_f.to_excel(writer, sheet_name='Sheet1')
workbook  = writer.book
worksheet = writer.sheets['Sheet1']
worksheet.set_column(0, 120, 15)
writer.save()

belg_results = merge_results('Belg') #Merge results for Belg season
belg_results.sort_values('FNID',axis=0,inplace=True) #Sort based on FNID
belg_results.set_index('FNID',inplace=True) #Set index to FNID
belg_results = belg_results[col_ord_final] #Set column order to order needed for GDHI - order specified in col_ord_final list.
belg_results = calc_average(belg_results)
belg_results_f = fallback_logic(belg_results,'Belg') #Implement fall back logic function
print('Export results for the Belg to Excel')
writer = pd.ExcelWriter('ET_Belg_results.xlsx',engine='xlsxwriter')
belg_results_f.to_excel(writer, sheet_name='Sheet1')
workbook  = writer.book
worksheet = writer.sheets['Sheet1']
worksheet.set_column(0, 120, 15)
writer.save()
print('Script Complete')