#-------------------------------------------------------------------------------
# Name:       WRSI Zonal Statistics
# Purpose:    Download selected WRSI file from USGS website, unzip it, and summarize WRSI data by adminstration units of interest using zonal statistics tools. 
#             Requires Arcpy and spatial analayst extension to run.
# Author:      Richard Barad, FEWS NET
#
# Created:    18/06/2020
# Copyright:  rbarad / FEWS NET 2020-2021
# Licence:    None
#-------------------------------------------------------------------------------

'''
This script downloads data from USGS WEbsite and runs zonal stats.
'''

import arcpy
import os
import requests
import zipfile
import sys

arcpy.env.overwriteOutput = True #Allow file overwrites

arcpy.CheckOutExtension("Spatial") #Checkout Spatial Analyst Extention - script requires access to a Spatial Analyst Extension to run 

baseurl = r'https://edcftp.cr.usgs.gov/project/fews/africa/east/dekadal/wrsi-chirps-etos' #url to USGS website where data can be downloaded

wrsi_folder = sys.argv[1]
print("The wrsi folder is " + wrsi_folder)
year_folder = sys.argv[2]
print("The year folder is " + year_folder)
month_folder = sys.argv[3]
print("The Month folder is " + month_folder)
file_download = sys.argv[4]
print("The download file is " + file_download)

file_split = file_download.split('_')
product = file_split[0]
folder = 'east' + product[1]
year = int(file_split[1])
month = int(file_split[2])
dekad = int(file_split[3])

def set_dekad():
    #Convert dekad of month to dekad on an annual 1-36 scale, file name on USGS website is in a 1-36 format, with values 1 through 9 written as 01,02, etc.
    dekad_annual = (month - 1) * 3 + dekad
    if dekad_annual < 10:
        dekad_string = '0' + str(dekad_annual)
    else:
        dekad_string = str(dekad_annual)
    return dekad_string 

url_dekad = set_dekad()

#Code below figures out the url, zipfile name, and tif file for the WRSI extended product based on the inputed parameters 

zipfilename = 'w' + str(year) + url_dekad + product + '.zip'
url = baseurl + '/' + folder + '/' + zipfilename
tiffile = 'w' + str(year) + url_dekad + 'eo.tif'

inpoly=os.path.join(wrsi_folder,'GDHI_Admin_Units.gdb\EA_GDHI_Admin_Units') #Set path to polygon featureclass, used for runnning zonal statistics

#Move to wrsi_folder
os.chdir(wrsi_folder)

#Create year folder in WRSI if it does not exist, and move into that directory
try:
    tiff_directory = os.path.join(os.getcwd(),str(year_folder))
    os.mkdir(tiff_directory)
    os.chdir(tiff_directory)
except:
    os.chdir(tiff_directory)

#Create month folder in WRSI folder if it does not exist, and move into that directory.
try:
    tiff_directory = os.path.join(os.getcwd(),str(month_folder))
    os.mkdir(tiff_directory)
    os.chdir(tiff_directory)
except:
    os.chdir(tiff_directory)

#Try to create a new folder called "tiffs" and then move to that directory- if it allready exists and was created through a previous run than just change to the directory.
try:
    tiff_directory = os.path.join(os.getcwd(),'Tiffs')
    os.mkdir(tiff_directory)
    os.chdir(tiff_directory)
except:
    os.chdir(tiff_directory)

def download_unzip_data(): #Download the WRSI File for the relevant year and save it to the workspace  
    WRSI_download = requests.get(url)
    print ("Download Status code: " + str(WRSI_download.status_code))
    if WRSI_download.status_code == 404:
        raise Exception( zipfilename + ' is not available on USGS website')
    else:
        open(zipfilename,'wb').write(WRSI_download.content) #Save zipped file to working directory
        print ("Extracting WRSI zipped file")
        with zipfile.ZipFile(zipfilename,'r') as zipobj: #Extract zipped file contents
            zipobj.extractall()
            print ("Zip file extracted")

download_unzip_data()

def reclass_raster(): #Reclass raster, set no start values to 0 (instead of 253) and yet to start values to Null/ no data (instead of 254) and return raster in memory
    print ("Reclassifying " + str(year) +" "+ product + " raster - set no start values to 0")
    outCon = arcpy.sa.Con(tiffile,0,tiffile,"value=253")
    print ("Reclassifying " + str(year) +" "+ product + " raster - set yet to start values to null")
    outSetNull = arcpy.sa.SetNull(outCon, outCon, "value=254")
    return outSetNull

def zonal_stats_updatetable():
    reclassed_raster = reclass_raster()
    #Run Zonal statistics on reclassified raster
    print ("Running Zonal Statistics for " + str(year) + " "+ product + " exported in memory")
    outtable= os.path.join('in_memory','zonal_stats') #set file path for results of zonal statistics, save in memory
    arcpy.env.workspace = os.path.join(wrsi_folder,'GDHI_Admin_Units.gdb') #Set workspace to GDB containing historical WRSI data
    arcpy.sa.ZonalStatisticsAsTable(inpoly,"FNID",reclassed_raster,outtable,"DATA","MEAN") #Run zonal statisitcs
    print ("Zonal Statistcs for " + str(year) + " "+ product + " exported in memory")
    feature_class = 'ea_wrsi_' + product #Figure out featureclass in workspace to update, based on WRSI product
    arcpy.management.MakeFeatureLayer(feature_class, 'GIS_layer') #Create layer from featureclass
    print ("Joining Zonal Statistics to Feature Class and update column")
    table_join = arcpy.management.AddJoin('GIS_layer', "FNID", outtable, "FNID", "KEEP_ALL") #Create join between layer and results of zonal statistics
    #Figure out which year column to update in feature class
    if product in ('et','e1') and month < 3: #If product is for short rains and month is January or February need to subtract one from year since column is dated by year of rains.
        col_update = feature_class + '.WRSI_' + str(year - 1)
    else:
        col_update = feature_class + '.WRSI_' + str(year)
    print(col_update)
    #Set appropriate year column in feature class to results of zonal statistics
    arcpy.management.CalculateField(table_join, col_update, "!zonal_stats.MEAN!", "PYTHON3", '', "TEXT", "NO_ENFORCE_DOMAINS")
    print("Join complete, removing join")
    arcpy.management.RemoveJoin(table_join)

zonal_stats_updatetable()

print ("Script complete")