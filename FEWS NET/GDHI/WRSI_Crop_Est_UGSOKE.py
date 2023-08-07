# -*- coding: utf-8 -*-
"""
Created on Tue Jun  1 14:00:23 2021
@author: rbarad

This script is used to calculate season crop production estimate to use for the GDHI based on WRSI - it outputs crop estimates Sorghum, Maize, and Cowpeas for each 
geographic unit in the the GDHI for the Long/Gu and Short/Deyr seasons from 2001 - present.This is V2 of the tool for making the calculations as the origional version was 
developed in excel. This script is for Somalia, Kenya, and Uganda. A seperate script is used for processing Ethiopia.

The two main inputs to the scripts are:
    1) Historical Crop production for SO and KE - downloaded from FDW
    2) WRSI data summarized by adminstrative unit stored in a Geodatabase

Both Somalia and Kenya use quantile-based approach in which percentile of WRSI is associated to percentile of production. The WRSI percentile for each geographic unit and 
WRSI product is calcuated by determining the percent rank of the WRSI seaons performance relative to the entire WRSI time series. The value from the crop production time series 
is then determined using the quantile pandas function, with the percent rank of WRSI as the quantile.
    
Some key notes on approach in Somalia:
    1) In Somalia, Long / Short Rains WRSI crop products are used for the Gu / Deyr seasons in most areas. In three admin1 units in Northern Somalia
    ('Woqooyi Galbeed','Awdal','Togdheer') the belg_grains product & long rangelands products are used. Belg Grains is used for the Karen season,long rangelands is used for Gu.
    2) Crop production data is only available at the Admin1 level for Adwal. Use same crop production data for all Admin2 units in Adwal.
    3) Seperate Maize and Grains WRSI datasets are available for the Long rains, Maize is used for Maize calcuations, and Grains for Sorghum and Cowpeas.
    4) In order to use the percentile approach at least five historical crop production data points are needed - if crop production data is not available for a crop then fall 
    back is included to ensure we have a time-series for each admin unit and crop. all back logic below:
        a) If no cowpeas estimate, use Sorghum for cowpeas
        b) If also no sorghum estimate use Maize for cowpeas
        b) If no sorghum estimate use Maize data for sorghum
        c) If no maize estimate use sorghum estimate for maize.

Some key notes on approach in Kenya:
    1) In Kenya, a percentile approach is also used. The same WRSI percent rank calcuation used in Somalia is also used in Kenya.
    2) In Kenya, there is not sufficient seasonal crop production data available, annual crop production time series is used in the qunatile calcuation - same time series used for both seasons.
    3) In Kenya, rangelands WRSI (long/short) products are used - this is because the GDHI only coveres Northern Kenya, and WRSI crop data does not cover most of Northern Kenya.
    
In Uganda, we do not have a crop production time series. Thus, the GDHI uses raw WRSI (1-100) as the input to the GDHI. 
Karamoja only has one crop production season, and long rains WRSI is used for this season. Maize is ued for Maize, and Grains is used for Sorghum and Cowpeas. 
"""

import pandas as pd
import math
import numpy as np
import arcpy
import arcgis 
import os
import sys

pd.options.mode.chained_assignment = None  # default='warn'

wrsi_folder = sys.argv[1]
year_folder = sys.argv[2]
month_folder = sys.argv[3]
arcpy.env.workspace = os.path.join(wrsi_folder,'GDHI_Admin_Units.gdb')

fc_list = arcpy.ListFeatureClasses() #Create list of feature classes from GDB containing WRSI Data
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
#This function imports WRSI data from feature classes into a dictionary of pandas dfs. Key in dictionary is the WRSI Product name, value is the df containing the data.
    print('Read WRSI Data')
    WRSI_data = {}
    for fc in fc_list:    
        fc_path = os.path.join(arcpy.env.workspace,fc)
        sdf = pd.DataFrame.spatial.from_featureclass(fc_path) #Import feature class into pandas df using fuction from ArcGIS Python API.
        sdf.set_index('FNID',inplace=True) #Make FNID the Index
        sdf.drop(['SHAPE'],inplace=True,axis=1) #Drop GIS/geometry column, which is included because we imported GIS data
        for col in ['WRSI_2020','WRSI_2021','WRSI_2022','WRSI_2023','WRSI_2024','WRSI_2025']:
            sdf[col] = sdf[col].astype(float)
        product = fc[-2:]
        full_product = get_product(product)
        WRSI_data[full_product] = sdf
    return WRSI_data

WRSI_data = get_wrsi_data()

#Excel Files to import containg crop production data 
so_crop_prod = r'.\Crop Production Data\SO_agprod_data.xlsx'
ke_crop_prod = r'.\Crop Production Data\KE_agprod_data.xlsx'

fnids = WRSI_data['MaizeL'].iloc[:,:7] #Get just FNIDs in a seperate Datafarame


def wrsi_rank(): 
#This function calcuates precentile rank for all five WRSI product for all areas that are part of analysis in KE/SO and writes results to a dictinary of dfs. 
    df_WRSI_percentile = {}
    for key, value in WRSI_data.items():
        print("Calculate wrsi percentiles for " + key)
        df_WRSI=WRSI_data[key]
        df_WRSI_KE_SO = df_WRSI[df_WRSI["ADMIN0"].isin(['Kenya','Somalia'])]
        #Percent ranking based on 2001 - 2015 data, decided to keep WRSI period of comparison static so tht historical estimates do not change between runs of the GDHI.
        df_new=df_WRSI_KE_SO.iloc[:,7:22].rank(axis=1, method='average', numeric_only=True, na_option='keep', ascending=True, pct=True)
        post2015_col = list(range(22,32))
        pre2015_col = list(range(7,22))
        for col in post2015_col: #Compute percent rank for all years after 2015, years after 2015 use data for 2002 - 2015 plus the current year
            year_col = df_WRSI_KE_SO.columns[col]
            rank_col_list = pre2015_col + [col]
            df_new[year_col] = (df_WRSI_KE_SO.iloc[:,rank_col_list] \
            .rank(axis=1, method='average', numeric_only=True, na_option='keep', ascending=True, pct=True)).loc[:,year_col]
        df_new=fnids.merge(df_new,left_index=True,right_index=True)
        df_WRSI_percentile[key] = df_new #Key in dictionary is the name of WRSI product - value is the df containing the percentiles.
    return df_WRSI_percentile

df_WRSI_percentile = wrsi_rank()

def set_so_rains(admin1):
#Function to set name for 2nd rainy season in Somalia, in three admin units in Northern SO rains are Gu/Karen instead of Gu/Deyr. These three admin units use different WRSI products.
    if admin1 in ('Woqooyi Galbeed','Awdal','Togdheer'):
        return 'Karen'
    else:
        return 'Deyr'

#Read / Clean Somalia Crop Production Data from FDW
class so_crop_data(): 
    def read_so_data():
        print("Read SO Crop Data")
        so_crop_raw = pd.read_excel(so_crop_prod,sheet_name ='SO_prod_FDW')
        return so_crop_raw
    
    def clean_so_data():
        so_crop = so_crop_data.read_so_data()
        print("Clean SO Crop Data")
        so_crop = so_crop[['fnid','admin_1','admin_2','period_date','season_name','season_year','value','product','crop_production_system','status']] #Select relevant columns
        so_crop = so_crop[so_crop['status'] != 'Not Collected'] #Filter out data which is null / Not Collected.
        so_crop = so_crop[so_crop['product'].isin(['Maize (Corn)','Sorghum','Cowpeas (Mixed)'])] #filter to only the relevant three crops
        so_crop['year'] = so_crop['season_year'].str[-4:].astype(int) #Create a year field
        so_crop['season_name'] = so_crop['season_name'].replace(to_replace='Deyr off-season', value='Deyr') #Replace Deyr Off-Season with Deyr
        so_crop['season_name'] = so_crop['season_name'].replace(to_replace='Gu off-season', value='Gu') #Replace Gu Off-Season with Gu
        so_crop['product'] = so_crop['product'].replace(to_replace='Maize (Corn)',value='Maize') #Simplify crop name
        so_crop['product'] = so_crop['product'].replace(to_replace='Cowpeas (Mixed)',value='Cowpeas') #Simplify crop name
        so_crop.loc[so_crop['admin_2'] == 'Afmadow', 'fnid'] = 'SO1990A22802' #Update FNIDs for Afmadow - Crop Production data has a different FNIDs for Afmadow - unsure why this is the case.
        return so_crop

so_crop_v1 = so_crop_data.clean_so_data()

#Continue to process and reformat crop production data form FDW
class pivot_clean_so_crop():    
    def so_pivot(df): #Aggregate SO Crop Production Data at admin2 level combine off-season data with regular season data
        so_pivot = df.pivot_table(index=['fnid','admin_1','admin_2','season_name','product'],columns='year',values='value',aggfunc='sum')
        so_pivot.reset_index(inplace=True)
        so_pivot['rains'] = so_pivot['admin_1'].apply(set_so_rains) #Figure out name of 2nd rainy season for each admin unit using function
        return so_pivot
    
    def adwal_case(): #Handle data for Adwal which reports at the Admin 1 level, set crop production for Admin2 units with production in Adwal equal to Admin 1 values for all crops / seasons and merge data
        so_crop_aggregate = pivot_clean_so_crop.so_pivot(so_crop_v1)
        df_so_list = []
        print("Handle Adwal Speacial Case")
        df_so_list.append(so_crop_aggregate)
        Awdal_admin2 = {'Borama':'SO1990A21101', 'Baki':'SO1990A21102'} 
        for key, value in Awdal_admin2.items(): #Create two identical dataframes containing data for Adwal - difference between them is that a different admin2 unit name & FNID is specified in each
            so_adwal = so_crop_v1[so_crop_v1['admin_1'] == 'Awdal'] 
            so_adwal = so_adwal.assign(admin_2=key) #Set values in Admin2 column equal to key
            so_adwal = so_adwal.assign(fnid=value) #Set values in FNID column equal to FNID for admin unit
            so_adwal_pivot = pivot_clean_so_crop.so_pivot(so_adwal)
            df_so_list.append(so_adwal_pivot) #Append to list
        so_crop_rev = pd.concat(df_so_list,ignore_index=True) #Merge together data for Adwal, with data for all other regions
        return so_crop_rev
    
    def cell_waq_case(): 
        #Function to handle data for Cell waq which does not have crop production data, set equal to Beled Xaawo which is a neighboring district.
        so_crop_rev = pivot_clean_so_crop.adwal_case()
        print("Handle Cell Waq Special Case")
        so_crop_rev_beled_xaawo = so_crop_rev[so_crop_rev['fnid'] == 'SO1990A22603']
        so_crop_rev_cell_waq = so_crop_rev_beled_xaawo.assign(admin_2='Ceel Waaq',fnid='SO1990A22604')
        so_crop_rev = pd.concat([so_crop_rev,so_crop_rev_cell_waq],ignore_index=True)
        return so_crop_rev
    
    def filter_data():
        # Function tofilter out production time series with less than 5 data points - can not use time series in qunatile function unless it has at least 5 data points.
        so_crop_rev = pivot_clean_so_crop.cell_waq_case()
        print("Filter out instances where there is not enough crop production data for quantile calcuations")
        so_crop_rev['count'] = so_crop_rev.count(axis=1,numeric_only=True) #Count the number of data points per season, geographic unit, crop combination
        so_crop_rev = so_crop_rev[so_crop_rev['count'] >= 5]
        so_crop_rev.drop(labels='count',axis=1,inplace=True) 
        return so_crop_rev

so_crop_final = pivot_clean_so_crop.filter_data() #Clean so crop data using chain of functions above

def set_so_wrsi_product(season,crop,second_rains):
    #Function to set WRSI Product to use for each row of crop production data
    if season == 'Gu' and crop == 'Maize' and second_rains == 'Deyr':
        return 'MaizeL'
    elif season == 'Gu' and second_rains == 'Deyr':
        return 'GrainsL'
    elif season == 'Gu' and second_rains == 'Karen': #Rangelands used in North Somalia as data for crop products not available for Gu season.
        return 'RangeL'
    elif season == 'Deyr' and second_rains == 'Karen': #Belg product used for Karen Rains in Northern Somalia
        return 'GrainsB'
    elif season == 'Deyr' and second_rains == 'Deyr': 
        return 'MaizeS'

def calc_quantile(quant,row): 
    #Function to calculate qunatile. If WRSI is nan set to nan, else calculate crop production estimate
    if math.isnan(quant) == True:
        return np.nan
    else:
        return row.quantile(quant)

#Calculate crop production for Somalia estimate based on percent ranking from WRSI data for each FNID, Crop, Season, and year combination for Somalia
col_list=[]
def calc_so_wrsi_prod_est():
    numeric_col = [col for col in so_crop_final.columns.tolist() if type(col) is int] #Select just columns containing crop production data (column names are intigers (i.e: Year))
    for year in range(2001,2026): 
        print ("Calcuate Crop Production Estimates for Somalia for " + str(year))
        new_col = "p" + str(year)
        col_list.append(new_col)
        for index, row in so_crop_final.iterrows(): #Loop through all rows for a specific year and calculate crop production estimate for each area
            fnid = row['fnid']
            wrsi_product = set_so_wrsi_product(row['season_name'],row['product'],row['rains']) #Select WRSI product to use for row
            #Get column name in WRSI dataset, show maize includes two years in heading
            col_name = 'WRSI_' + str(year)
            wrsi_pct_df = df_WRSI_percentile[wrsi_product] #Select appropriate df with percentiles based on product
            quant = wrsi_pct_df.loc[fnid,col_name] #Get quantile for year
            row = row.loc[numeric_col].astype(float) #Select just columns from the row which contain annual WRSI data - column names are type numeric
            v = calc_quantile(quant,row) #Calcuate crop production for year / area using quantile function
            so_crop_final.loc[index, new_col] = v #write crop production estimate to datafarame
    return so_crop_final

def transform_so_data(): #Transform WRSI production estimate data into format needed for GDHI and create seperate dfs for Gu and Deyr, implement fall back logic to fill NAs
    print('Transform SO Results into appropriate format')
    seasons= ['Gu','Deyr']
    so_fnids = fnids[fnids['COUNTRY'] == 'SO']
    so_results = {}
    for season in seasons:
        #Transporm data into seperate datasets for Deyr & Gu and pivot data so that there are seperate columns for each crop and year
        so_crop_filt = so_wrsi_crop_est[so_wrsi_crop_est['season_name'] == season] #Filter data to only include one season
        so_crop_pivot = so_crop_filt.pivot_table(index='fnid',columns='product',values=col_list,dropna=False) #pivot to match format needed for GDHI
        so_crop_pivot.columns = ['_'.join(col).strip() for col in so_crop_pivot.columns.values] #Strip column names so that they are a strings instead of tuple
        so_crop_pivot = so_fnids.merge(so_crop_pivot,left_index=True,right_index=True,how='left') #Merge to full FNIDS so that output table includes all Admin2 FNIDs, even areas without crop production.
        #Implement fall back logic to fill in as many N/As as possible
        print('Implement fallback logic for SO' + season + 'results')
        for col in col_list:
            maize_col = col + '_Maize'
            sorghum_col = col + '_Sorghum'
            cowpeas_col = col + '_Cowpeas'
            so_crop_pivot[cowpeas_col].fillna(so_crop_pivot[sorghum_col], inplace=True)
            so_crop_pivot[cowpeas_col].fillna(so_crop_pivot[maize_col], inplace=True)
            so_crop_pivot[sorghum_col].fillna(so_crop_pivot[maize_col], inplace=True)
            so_crop_pivot[maize_col].fillna(so_crop_pivot[sorghum_col], inplace=True)
            #Save results to a dictionary with season name as key
        so_results[season] = so_crop_pivot
    return so_results

so_wrsi_crop_est = calc_so_wrsi_prod_est()
so_results = transform_so_data()

#Export SO data to a csv - can activitate if you want to just results for SOmalia instead of all results
#so_results['Gu'].to_csv('SO_crop_rev_gu_fallback.csv')
#so_results['Deyr'].to_csv('SO_crop_rev_deyr_fallback.csv')


class ke_crop_data():
    #Chain of functions to read and clean KE Crop production data from FDW    
    def read_ke_data(): #Read KE Crop Production data into df
        print('Read KE Crop Data')
        ke_crop_raw = pd.read_excel(ke_crop_prod,sheet_name ='KE_prod_FDW')
        return ke_crop_raw
    
    def clean_ke_data(): #Clean / pivot KE Crop Data
        print('Clean KE Crop Data')
        ke_crop = ke_crop_data.read_ke_data()
        ke_crop = ke_crop[['fnid','admin_1','admin_2','period_date','season_name','season_year','value','product','status']] #Select relevant columns
        ke_crop = ke_crop[ke_crop['status'] != 'Not Collected'] #Filter out not collected data
        ke_crop = ke_crop[ke_crop['product'].isin(['Maize Grain (White)'])] #filter to only the relevant crop
        ke_crop['year'] = ke_crop['season_year'].str[-4:].astype(int) #Create a year field
        ke_crop['product'] = ke_crop['product'].replace(to_replace='Maize (Corn)',value='1_Maize') #Simplify name
        ke_crop.loc[ke_crop['year'] < 2015, 'admin_1'] = ke_crop['admin_2'] #Move Admin2 units to Admin 1 column to account for old admin unit structure present before 2015
        ke_crop = ke_crop[ke_crop['admin_1'].isin(['Mandera','Wajir','Turkana','Marsabit'])] #Filter to just include admin 1 units in GDHI
        ke_crop = ke_crop.pivot_table(index='admin_1',columns='year',values='value',aggfunc='sum') #Pivot data (data for each year in seperate columns) and aggregate data
        return ke_crop

def calc_ke_wrsi_prod_est(): 
    #Function to calcuation WRSI based crop production estimates for Long and Short rains in Kenya based on percent ranking for each FNID, for each year
    ke_results = {}
    for season in ['L','S']: #L stands for L, S standard for short
        wrsi_product = 'Range' + season
        ke_pct = df_WRSI_percentile[wrsi_product] #Get percent rank for select product
        ke_pct = ke_pct[ke_pct['ADMIN0'] == 'Kenya'] #Filter WRSI percent ranks to just included data for Kenya
        for year in range(2001,2026):
            print('Calculate crop production estimates for Kenya for ' + str(year) + ' ' + season + ' Rains' )
            maize_col = ('p' + str(year) + '_Maize')
            ke_pct.loc[:,maize_col] = np.nan
            col_name = 'WRSI_' + str(year) 
            for index, row in ke_pct.iterrows(): #Loop through all rows for a specific year and calculate crop production estimate for each area
                admin1 = row['ADMIN1']
                quant = row[col_name]
                time_series = ke_crop_data.loc[admin1]
                v = calc_quantile(quant,time_series)
                ke_pct.loc[index,maize_col] = v
            sorghum_col = ('p' + str(year) + '_Sorghum') #Set Sorghum estimates equal to Maize, both crops use same WRSI and crop production time series in Kenya so values will be equal.
            cowpea_col = ('p' + str(year) + '_Cowpeas') 
            ke_pct.loc[:,sorghum_col] = ke_pct.loc[:,maize_col] #Set Sorghum estimates equal to Maize, both crops use same WRSI and crop production time series in Kenya so values will be equal.
            ke_pct.loc[:,cowpea_col] = -99 #Set Cowpeas equal to -99 - no Cowpeas production in KE
            ke_pct.drop(col_name,axis=1,inplace=True) #Drop year column with origional WRSI value, not needed in final output.
        ke_results[season] = ke_pct
    return ke_results
 
ke_crop_data = ke_crop_data.clean_ke_data()      
ke_WRSI_crop_est = calc_ke_wrsi_prod_est()

#You can turn on these functions if you want to view just the results for Kenya
#ke_WRSI_crop_est['long'].to_csv('KE_crop_rev_long.csv')
#ke_WRSI_crop_est['short'].to_csv('KE_crop_rev_short.csv') 

#Handle UG Data

def get_crop(product):
    if product == 'MaizeL':
        return 'Maize'
    elif product == 'GrainsL':
        return 'Sorghum'

class ug_process_wrsi():
    #This fucntion gets the long rains WRSI data for Maize and Grains for Karamoja, returns a list with two dfs, one more for Maize and one for Sorghum
    def process():
        print ('Proces UG WRSI Data')
        ug_wrsi_all= []
        for product in ['MaizeL','GrainsL']:
            crop = get_crop(product)
            wrsi = WRSI_data[product]
            ug_wrsi = wrsi[wrsi['COUNTRY'] == 'UG']
            for year in range(2001,2026):
                col = 'p' + str(year) + '_' + crop
                wrsi_col = 'WRSI_' + str(year)
                ug_wrsi.loc[:,col] = ug_wrsi.loc[:,wrsi_col]
                ug_wrsi.drop(wrsi_col,axis=1,inplace=True)
            ug_wrsi_all.append(ug_wrsi)
        return ug_wrsi_all
                
    def merge():
        #This fucntion merges together the long and Maize grains WRSI data into one df.
        ug_wrsi_list = ug_process_wrsi.process()
        cols_to_use = ug_wrsi_list[0].columns.difference(ug_wrsi_list[1].columns) #This is so that output does not include columns present in both dfs
        ug_wrsi_final = ug_wrsi_list[1].merge(ug_wrsi_list[0][cols_to_use],left_index=True,right_index=True)
        return ug_wrsi_final

ug_wrsi_results = ug_process_wrsi.merge()
ug_fnids = fnids[fnids['COUNTRY'] == 'UG']

#Merge results together for all three countries
def concat_ke_so_ug_data():
    os.chdir(os.path.join(wrsi_folder,year_folder,month_folder))
    print('Merge results and export to Excel')
    long_results = pd.concat([ke_WRSI_crop_est['L'],so_results['Gu'],ug_wrsi_results]) #Concatenate, results for Uganda, Somalia, and Kenya for Gu/Long Season
    #Calculate averages - averages are only through 2020 so that that they do not change over time
    long_results['Maize_av'] = long_results[['p2001_Maize','p2002_Maize','p2003_Maize','p2004_Maize','p2005_Maize','p2006_Maize','p2007_Maize','p2008_Maize','p2009_Maize','p2010_Maize','p2011_Maize', \
                                             'p2012_Maize','p2013_Maize','p2014_Maize','p2015_Maize','p2016_Maize','p2017_Maize','p2018_Maize','p2019_Maize','p2020_Maize']].mean(axis=1)
    long_results['Sorghum_av'] = long_results[['p2001_Sorghum','p2002_Sorghum','p2003_Sorghum','p2004_Sorghum','p2005_Sorghum','p2006_Sorghum','p2007_Sorghum','p2008_Sorghum','p2009_Sorghum','p2010_Sorghum', \
                                               'p2011_Sorghum','p2012_Sorghum', 'p2013_Sorghum','p2014_Sorghum','p2015_Sorghum','p2016_Sorghum','p2017_Sorghum','p2018_Sorghum','p2019_Sorghum','p2020_Sorghum']].mean(axis=1)
    long_results['Cowpeas_av'] = long_results[['p2001_Cowpeas','p2002_Cowpeas','p2003_Cowpeas','p2004_Cowpeas','p2005_Cowpeas','p2006_Cowpeas','p2007_Cowpeas','p2008_Cowpeas','p2009_Cowpeas','p2010_Cowpeas',\
                                               'p2011_Cowpeas','p2012_Cowpeas', 'p2013_Cowpeas','p2014_Cowpeas','p2015_Cowpeas','p2016_Cowpeas','p2017_Cowpeas','p2018_Cowpeas','p2019_Cowpeas','p2020_Cowpeas']].mean(axis=1)
    long_results.drop(['OBJECTID','PCODE'],axis=1,inplace=True)
    long_results.fillna(-99,inplace=True) #Set instances of no data to -99
    #Write results to Excel
    writer = pd.ExcelWriter('KEUGSO_long_results.xlsx',engine='xlsxwriter')
    long_results.to_excel(writer, sheet_name='Sheet1')
    worksheet = writer.sheets['Sheet1']
    worksheet.set_column(0, 120, 15)
    writer.save()
    
    #Calculate averages - averages are only through 2020 so that that they do not change over time
    short_results = pd.concat([ke_WRSI_crop_est['S'],so_results['Deyr'],ug_fnids]) #Concatenate, results for Uganda, Somalia, and Kenya for Gu/Long Season - Uganda rows will be blank as no short rains in Karamoja.
    short_results.drop(['OBJECTID','PCODE'],axis=1,inplace=True)
    short_results['Maize_av'] = short_results[['p2001_Maize','p2002_Maize','p2003_Maize','p2004_Maize','p2005_Maize','p2006_Maize','p2007_Maize','p2008_Maize','p2009_Maize','p2010_Maize','p2011_Maize', \
                                             'p2012_Maize','p2013_Maize','p2014_Maize','p2015_Maize','p2016_Maize','p2017_Maize','p2018_Maize','p2019_Maize','p2020_Maize']].mean(axis=1)
    short_results['Sorghum_av'] = short_results[['p2001_Sorghum','p2002_Sorghum','p2003_Sorghum','p2004_Sorghum','p2005_Sorghum','p2006_Sorghum','p2007_Sorghum','p2008_Sorghum','p2009_Sorghum','p2010_Sorghum', \
                                               'p2011_Sorghum','p2012_Sorghum', 'p2013_Sorghum','p2014_Sorghum','p2015_Sorghum','p2016_Sorghum','p2017_Sorghum','p2018_Sorghum','p2019_Sorghum','p2020_Sorghum']].mean(axis=1)
    short_results['Cowpeas_av'] = short_results[['p2001_Cowpeas','p2002_Cowpeas','p2003_Cowpeas','p2004_Cowpeas','p2005_Cowpeas','p2006_Cowpeas','p2007_Cowpeas','p2008_Cowpeas','p2009_Cowpeas','p2010_Cowpeas',\
                                               'p2011_Cowpeas','p2012_Cowpeas', 'p2013_Cowpeas','p2014_Cowpeas','p2015_Cowpeas','p2016_Cowpeas','p2017_Cowpeas','p2018_Cowpeas','p2019_Cowpeas','p2020_Cowpeas']].mean(axis=1)
    short_results.fillna(-99,inplace=True) #Set instances of no data to -99
    #Write resulrs to Excel
    writer = pd.ExcelWriter('KEUGSO_short_results.xlsx',engine='xlsxwriter')
    short_results.to_excel(writer, sheet_name='Sheet1')
    worksheet = writer.sheets['Sheet1']
    worksheet.set_column(0, 120, 15)
    writer.save()

concat_ke_so_ug_data()

print("Script Complete")