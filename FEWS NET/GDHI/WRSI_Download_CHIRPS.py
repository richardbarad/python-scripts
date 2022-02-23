#-------------------------------------------------------------------------------
# Name:       WRSI Zonal Statistics
# Purpose:    Download selected WRSI file from USGS website, unzip it, and summarize WRSI data by adminstration units of interest using zonal statistics tools. Requires Arcpy and spatial analayst extension to run.
# Author:      Richard Barad, FEWS NET
#
# Created:     18/06/2020
# Copyright:   (c) rbarad / FEWS NET 2020-2021
# Licence:    None
#-------------------------------------------------------------------------------

'''
This script downloads data 
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

variables ={} #set set_url_filenames() & set_other_variables functions write to this dictionary

file_split = file_download.split('_')
print(file_split)
product = file_split[0]
year = int(file_split[1])
month = int(file_split[2])
dekad = int(file_split[3])

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

def set_url_filenames(): #Figure out the components of url for downloading the data based on the product, year, and dekad
    print('Creating url and file name variables based on selected product')
    #Convert dekad of month to dekad on an annual 1-36 scale, file name on USGS website is in a 1-36 format, with values 1 through 9 written as 01,02, etc.
    dekad_m = (month - 1) * 3 + dekad
    if dekad_m < 10:
        url_dekad = '0' + str(dekad_m)
    else:
        url_dekad = str(dekad_m)
    if product == 'MaizeL':
        url_product = 'ee'
        folder = 'easte'
    elif product == 'GrainsL':
        url_product = 'el'
        folder = 'eastl'
    elif product == 'GrainsB':
        url_product = 'ek'
        folder = 'eastk'
    elif product == 'RangeL':
        url_product = 'e2'
        folder = 'east2'
    elif product == 'RangeS':
        url_product = 'e1'
        folder = 'east1'
    elif product == 'MaizeS':
        url_product = 'et'
        folder = 'eastt'
    #Set variables - write to variables dictionary, variables used latter in other functions.
    variables['folder'] = folder #Name of folder containing data, based on product
    variables['zipfilename'] = 'w' + str(year) + url_dekad + url_product + '.zip' #Full name of zip file to download from USGS website
    variables['url_product'] = url_product #two letter code for product (ee,el,ek,e2,e1,or et)
    variables['filename']= 'w' + str(year) + url_dekad + 'eo' #eo is name of the file for the WRSI extended, zipped file download includes multiple tiff files for different WRSI products.

def download_unzip_data(): #Download the WRSI File for the relevant year and save it to the workspace
    zipfilename = variables['zipfilename']
    url = baseurl + '/' + variables['folder'] + '/' + zipfilename
    print ("Downloading WRSI file at" + url)
    WRSI_download = requests.get(url,verify=False)
    print ("Download Status code: " + str(WRSI_download.status_code)) #make sure status code is not 404, if 404 the file likely does not exist on USGS website and script will not run in full
    open(zipfilename,'wb').write(WRSI_download.content) #Save zipped file to working directory
    print ("Extracting WRSI zipped file")
    with zipfile.ZipFile(zipfilename,'r') as zipobj: #Extract zipped file contents
        zipobj.extractall()
    print ("Zip file extracted")

set_url_filenames()
download_unzip_data()

def reclass_raster(): #Reclass raster, set no start values to 0 and yet to start values to Null (no data) and return raster in memory
    tifilename= variables['filename'] + '.tif'
    print ("Reclassifying " + str(year) +" "+ product + " raster - set no start values to 0")
    outCon = arcpy.sa.Con(tifilename,0,tifilename,"value=253")
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
    feature_class = 'ea_wrsi_' + variables['url_product'] #Figure out featureclass in workspace to update, based on WRSI product
    arcpy.management.MakeFeatureLayer(feature_class, 'GIS_layer') #Create layer from featureclass
    print ("Joining Zonal Statistics to Feature Class and update column")
    table_join = arcpy.management.AddJoin('GIS_layer', "FNID", outtable, "FNID", "KEEP_ALL") #Create join between layer and results of zonal statistics
    #Figure out which year column to update in feature class
    if product in ('RangeS','MaizeS') and month < 3: #If product is for short rains and month is January or February need to subtract one from year since column is dated by year of rains.
        col_update = feature_class + '.WRSI_' + str(year - 1)
    else:
        col_update = feature_class + '.WRSI_' + str(year)
    #Set appropriate year column in feature class to results of zonal statistics
    arcpy.management.CalculateField(table_join, col_update, "!zonal_stats.MEAN!", "PYTHON3", '', "TEXT", "NO_ENFORCE_DOMAINS")
    print("Join complete, removing join")
    arcpy.management.RemoveJoin(table_join)

zonal_stats_updatetable()

print ("Script complete")