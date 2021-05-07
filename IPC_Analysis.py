# -*- coding: utf-8 -*-
"""
Created on Mon Jan 25 12:30:51 2021
@author: rbarad

This script can be used to calculate the Average IPC Phase, Percent of Cycles in IPC Phase 3+, Percent of Cycles in IPC Phase 2+ based on historical IPC Data.
Requires using the ArcGIS Python API which is available with default installation of ArcGIS Pro starting with ArcGIS Pro 2.5.x.
Also requires xlsxwriter, a python package for creating excel files which can also be installed through ArcGIS Pro.

Requires two inputs:
1) A csv containing the historical outlook data in current mapping units (CS, ML1, or ML2 data) - provided by data team.
2) The shapefile associated with the mapping units in the csv (Note that shapefile name cannot include a dot)

The script will:
1) Import csv into pandas dataframe, and calculate long term IPC trends
2) Join long term trend data to the admin / LHZ names associated with each area from shapefile, delete unnecessary fields (i.e: FID, EFF_YEAR) from the shapefile, and sort the data
3) Export results to an Excel file, and make sure the Excel file is easy to read / formatted nicely (i.e: Percentages displayed as a percent)
"""

import pandas as pd
from arcgis.features import GeoAccessor, GeoSeriesAccessor
import os
import matplotlib.pyplot as plt
import requests
import datetime

os.chdir(r'C:\Users\rbarad.CHEMONICS_HQ\OneDrive - Chemonics\Hot Spot Profiles\IPC Analysis\HT')

#Set input files to IPC csv, food security shapefile (cannot include a "." in shapefile name) and output Excel file
params = {'country'       : 'HT',
          'IPC_csv'       : 'HT_Admin3_LHZ_2015_3_ML1.csv',
          'fsc_shapefile' : r'HT_Admin3_LHZ_2015_3.shp', #Shapefile name must not include a "." in the file name - only dot should be . before shp (i.e: ".shp").
          'outputfile'    : 'HT_IPC_Analysis_ML1.xlsx',
          'IPC_Aggregation': True, #Set to true is you want to aggregate data to a higher level and produce graphs 
          'IPC_Aggregation_Level':'LHZ_Admin1' #Options are LHZ_Admin1 or LHZ or Admin1
          }

def read_clean_data(): #Read csv into dataframe and make the FNID the index
    print("Read CSV into dataframe")
    fs_data = pd.DataFrame(pd.read_csv(params['IPC_csv']))
    fs_data.rename(columns = {"Unnamed: 0" : "FNID"}, inplace = True)
    fs_data.set_index("FNID", inplace = True)
    return fs_data

fs_data_df = read_clean_data()
outlook_count = len(fs_data_df.columns) #Count the number of columns in dataframe, represents the number of outlook cycles in the data

class calc_IPC(): #Calculate Long Term IPC Trends
    def ipc_av(): #Calculate the average IPC Phase, round to two significant figures
        fs_data_df["IPC_avg"]=fs_data_df.iloc[:,0:outlook_count].mean(axis=1)
        fs_data_df["IPC_avg"]=fs_data_df["IPC_avg"].round(2)
        return fs_data_df

    def ipc_3plus(): #Calculate the percent of cycles in IPC Phase 3+
        fs_data_df = calc_IPC.ipc_av()
        IPC3plus=fs_data_df.iloc[:,0:outlook_count] >= 3
        fs_data_df["IPC_3plus"]=IPC3plus.sum(axis=1) / outlook_count
        return fs_data_df

    def ipc_2plus(): #Calcuate the percent of cycles in IPC Phase 2+
        fs_data_df = calc_IPC.ipc_3plus()
        IPC2plus=fs_data_df.iloc[:,0:outlook_count] >= 2
        fs_data_df["IPC_2plus"]=IPC2plus.sum(axis=1) / outlook_count
        return fs_data_df

#Import shapefile as a pandas dataframe. This uses the ArcGIS Python API to import the shapefile as a spatially enabled dataframe
#https://developers.arcgis.com/python/guide/introduction-to-the-spatially-enabled-dataframe/
class read_clean_shapefile():
    def read_shapefile():
        print("Read Shapefile into Dataframe")
        shapefile = pd.DataFrame.spatial.from_featureclass(params['fsc_shapefile'])
        shapefile.set_index('FNID', inplace = True)
        return shapefile

    def clean_shapefile():
        #Identify which columns need to be deleted, any columns not in keep column list will be deleted from dataframe created from shapefile (i.e: EFF_YEAR, FID, EFF_PERD)
        print("Clean Shapefile, remove not needed collumns")
        shapefile = read_clean_shapefile.read_shapefile()
        keep_columns=['COUNTRY','ADMIN0','ADMIN1','ADMIN2','ADMIN3','ADMIN4','LZCODE','LZNAME']
        columnlist = shapefile.columns
        remove_columns =[]
        for column in columnlist:
            delete_column = column not in keep_columns
            if delete_column==True:
                remove_columns.append(column)
        #Delete uncessary columns (columns in remove_columns list) from the shapefile dataframe
        clean_shapefile = shapefile.drop(remove_columns,axis=1)
        return clean_shapefile

class sort_export_data(): #Sort data and export to Excel - ensure formating to make sure Excel file is easy for end user to read
    def sort_data(): #Sort dataframe values by LZCODE, Admin1, Admin2 if LH Zone Name is present. If shapefile is not a LH Zone intersect shapefile just sort by admin names
        if lhz == True:
            join.sort_values(by=['LZCODE','ADMIN1','ADMIN2'],axis=0,inplace=True)
        else:
            join.sort_values(by=['ADMIN1','ADMIN2'],axis=0,inplace=True)
        return join

    def export_format_excel():
        #Get column numbers in dataframe for IPC 2 plus,IPC 3 Plus, and LZNAME columns
        print ("Sorting data and Exporting to Excel File")
        IPC2plus_col=join.columns.get_loc("IPC_2plus")
        IPC3plus_col=join.columns.get_loc("IPC_3plus")
        if lhz ==True:
            LZNAME_col=join.columns.get_loc("LZNAME")
        #Covert column numbers in dataframe to letter column in Excel, using ord and chr functions, (ord('@') returns 64, then numbers 65 - 90 represent upercase letters (A-Z)
        #Add two to column number to account for the Index/FNID (A in Excel file), and the 0 column (Column B in Excel)
        #https://stackoverflow.com/questions/23199733/convert-numbers-into-corresponding-letter-using-python
        Excel_IPC3plus = chr(ord('@')+IPC3plus_col+2)
        Excel_IPC2plus = chr(ord('@')+IPC2plus_col+2)
        IPC_excelrange=str(Excel_IPC3plus)+":"+Excel_IPC2plus
        if lhz==True:
            Excel_LZNAME = chr(ord('@')+LZNAME_col+2)
            LZNAME_excelrange=Excel_LZNAME+":"+Excel_LZNAME
        #Export to an Excel file
        excelwriter=pd.ExcelWriter(params['outputfile'],engine='xlsxwriter')
        sort_export_data.sort_data().to_excel(excelwriter)
        #Format excel file values as % using xlsxwriter and make LZNAME and FNID columns wider to account for their longer length
        workbook = excelwriter.book
        worksheet = excelwriter.sheets['Sheet1']
        percent_fmt = workbook.add_format({'num_format': '0.00%', 'bold': False})
        worksheet.set_column(IPC_excelrange, 10, percent_fmt)
        worksheet.set_column('A:A',20)
        if lhz==True:
            worksheet.set_column(LZNAME_excelrange,50)
        #Save Excel file and close
        print ("Saving Excel File")
        excelwriter.save()
        excelwriter.close()

fs_data_av_df = calc_IPC.ipc_2plus()
fs_data_df.drop(fs_data_df.iloc[:,0:outlook_count],inplace=True,axis=1) #Remove columns which do not include averages, percentages
shapefile_df = read_clean_shapefile.clean_shapefile()

join = shapefile_df.join(fs_data_av_df) #Join the shapefile dataframe to the dataframe containing the historical IPC Calcuations

columnlist = shapefile_df.columns #Check if shapefile includes a livelihood zone intersect, lhz variable used in sort_export_data functions.
if "LZNAME" in columnlist:
    lhz = True
else:
    lhz = False

sort_export_data.export_format_excel()

#The Additional section of the script below is optional and is used to aggregate data and create graphs - when aggregating landscan data from FDW is used. Requires login to the FEWS NET Data Warehouse.

def set_ag_columns():    
    if params['IPC_Aggregation_Level'] == 'LHZ_Admin1':
        ag_columns = ['ADMIN1','LZCODE']
    elif params['IPC_Aggregation_Level'] == 'LHZ':
        ag_columns = ['LZCODE']
    elif params['IPC_Aggregation_Level'] == 'Admin1':
        ag_columns = ['ADMIN1']
    return ag_columns

class get_join_landscan_pop():
    def get_landscan():
        landscan_url=r'https://fdw.fews.net/api/geographicunit/?country=' + params['country'] + '&unit_type=fsc_admin_lhz&as_of_date=' + str(datetime.date.today()) + '&format=json&fields=with_population'
        print("Get landscan data from FDW API")
        r = requests.get(landscan_url)
        landscan = pd.read_json(r.text)
        landscan.set_index('fnid',inplace=True)
        return landscan
    def join_landscan():
        api_landscan = get_join_landscan_pop.get_landscan()
        ipc_landscan_join = join.merge(api_landscan[['estimated_population']],left_index=True,right_index=True)
        return ipc_landscan_join
        
def calc_pop_weights(): #Get Total LH/Admin 1 or LH Population and join back to IPC Dataframe, calculate percentage of total population at higher level unit for each mapping unit
    ipc_df = get_join_landscan_pop.join_landscan()
    ag_columns = set_ag_columns()
    admin2sum = ipc_df.groupby(ag_columns,as_index=False)[['estimated_population']].sum()
    admin2sum.rename({'estimated_population':'aggregate_pop'},axis=1,inplace=True)
    ipc_df = ipc_df.merge(admin2sum,on=ag_columns)
    ipc_df['pct'] = ipc_df['estimated_population'] / ipc_df['aggregate_pop']
    #Multiply IPC values by percentages, and sum together results of multiplication (this calculates a weigted average in which all admin units within an LH Zone are weighted based on thier population)
    print("Calculate aggreagated Average IPC Phase and Percent of Cyles in IPC Phase 3 plus, apply weigted average")
    ipc_df['ipc_avg_weight'] = ipc_df['IPC_avg'] * ipc_df['pct']
    ipc_df['ipc_3plus_weight'] = ipc_df['IPC_3plus'] * ipc_df['pct']
    ipc_df['ipc_2plus_weight'] = ipc_df['IPC_2plus'] * ipc_df['pct']
    return ipc_df

def aggregate_data(): #Aggregate data to the selected higher level using calculated weights - multiply IPC 3+ and IPC 2+ results by 100 to convert to a percentage
    ipc_df = calc_pop_weights()
    if params['IPC_Aggregation_Level'] == 'LHZ_Admin1':
        ipc_df['LHZ_Admin1'] = ipc_df['LZCODE'] + ' ' + ipc_df['ADMIN1']
        IPC_Agg = ipc_df.groupby(['LHZ_Admin1'],as_index=False)[['ipc_avg_weight','ipc_3plus_weight','ipc_2plus_weight']].sum()
        IPC_Agg.set_index('LHZ_Admin1',inplace=True)
    elif params['IPC_Aggregation_Level'] == 'LHZ':
        IPC_Agg = ipc_df.groupby(['LZCODE'],as_index=False)[['ipc_avg_weight','ipc_3plus_weight','ipc_2plus_weight']].sum()
        IPC_Agg.set_index('LZCODE',inplace=True)
    elif params['IPC_Aggregation_Level'] == 'Admin1':
        IPC_Agg = ipc_df.groupby(['ADMIN1'],as_index=False)[['ipc_avg_weight','ipc_3plus_weight','ipc_2plus_weight']].sum()
        IPC_Agg.set_index('ADMIN1',inplace=True)
    IPC_Agg['ipc_3plus_weight']=IPC_Agg['ipc_3plus_weight'] * 100
    IPC_Agg['ipc_2plus_weight']=IPC_Agg['ipc_2plus_weight'] * 100
    return IPC_Agg

class make_charts():
    plt.rcParams["figure.figsize"] = [9,6]
    def phase3_chart():
        ipc_agg_df.plot(y='ipc_3plus_weight',kind='bar',rot=-80)
        plt.ylabel("Percent in IPC 3 plus")
        plt.title("Average Percent of Cycles in IPC Phase 3+")
        plt.tight_layout()
        plt.savefig(params['IPC_Aggregation_Level'] + '_IPC_3plus.png')
        plt.show()
    def av_ipc_chart():
        ipc_agg_df.plot(y='ipc_avg_weight',kind='bar',rot=-80)
        plt.ylabel("IPC Area Phase")
        plt.ylim((1,ipc_agg_df['ipc_avg_weight'].max()+0.2))
        plt.title("Average IPC Area Phase")
        plt.tight_layout()
        plt.savefig(params['IPC_Aggregation_Level'] + '_IPC_Av.png')
        plt.show()

if params['IPC_Aggregation'] == True:
    ipc_agg_df = aggregate_data()
    
    make_charts.phase3_chart()
    make_charts.av_ipc_chart()

print("Script Complete")













