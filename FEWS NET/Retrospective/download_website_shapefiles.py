# -*- coding: utf-8 -*-
"""
Created on Fri Jun  9 10:19:44 2023
This scripts performs the following steps:
    1) Download the regional shapefiles from the website for the selected date
    2) Unzip the shapefiles
    3) Merge the ML1 shapefiles together into a global ML1 shapefile
    4) Add 1 to ML1 value in areas with !s included in the mapping
    5) Remove 99 (No data) and 88 (water) from ML1 shapefile
    6) Convert global ML1 shapefile to global ML1 raster and output raster in selected folder
    7) Steps 3-6 are then repeated for ML2

@author: rbarad
"""
import requests
from zipfile import ZipFile
import glob
import os
import arcpy

#Sometimes a permission denied error happens and I am not sure why, when this occurs close the script, reopen it, and then try running it again.
directory = r'C:\Users\rbarad\OneDrive - Chemonics\Desktop\Dump' #Directory where intermediate files will be saved, should be an empty folder - files are deleted at the end of this script, folder must be emptry for script to run correctly
raster_folder = r'M:\EW Evaluation Maps\Global_ipc_rasters' #Directory where rasters will be saved
date='2023-02-01'

downloads = {'east_africa':'https://fdw.fews.net/api/ipcpackage/region/902/',
             'west_africa':'https://fdw.fews.net/api/ipcpackage/region/901/',
             'southern_africa':'https://fdw.fews.net/api/ipcpackage/region/903/',
             'LAC':'https://fdw.fews.net/api/ipcpackage/region/904/',
             'AF':'https://fdw.fews.net/api/ipcpackage/country/AF/'} #Need to remove AF if runnning the script for period when AF was not a presence country

#Set arcgis workspace to directory and move to working directory so all downloads and script outputs are saved in this folder
os.chdir(directory)
arcpy.env.workspace = directory
arcpy.env.overwriteOutput = True

print('Downloading files')
for region,url in downloads.items():
    url2 = url + date
    r = requests.get(url2, allow_redirects=True)
    zipfilename = region + '.zip'
    open(zipfilename, 'wb').write(r.content)
    with ZipFile(zipfilename, 'r') as zipobj:
        zipobj.extractall()

#Create Global ML1 shapefile and Clean
print('Find ML1 shapefiles')
file_path = directory + '\\*ML1.shp' 
ML1files = glob.glob(file_path) #Get list of file paths for all ML1 Shapefiles
print('The list of ML1 shapefiles are ' + ' , '.join(ML1files))
ML1global_shapefile = 'Global_' + date[:4] + date[5:7] + "_ML1.shp"
print('Merging together ML1 shapefiles, and add HA1 value to ML1 value, and delete no data and national park')
arcpy.management.Merge(ML1files,ML1global_shapefile) #Merge together all ML1 shapefiles
arcpy.management.CalculateField(ML1global_shapefile, "ML1_adj", "!ML1!+!HA1!", "PYTHON3", '', "SHORT", "NO_ENFORCE_DOMAINS") #Add ML1 and HA1 values together
arcpy.MakeTableView_management(ML1global_shapefile, "View") #Create a view
arcpy.SelectLayerByAttribute_management("View","NEW_SELECTION", 
                                        'ML1 IN (99, 88)') #Select values of 99 and 88 from global shapefiles
arcpy.DeleteRows_management("View") #Delete values of 99 and 88
#Create ML1 Raster
print('Converting ML1 Shapefile to Raster')
ML1_output_file= os.path.join(raster_folder, "Global_" + date[:4] + date[5:7] + "_ML1.tif")
arcpy.conversion.PolygonToRaster(ML1global_shapefile, "ML1_adj", ML1_output_file , "CELL_CENTER", "NONE", 0.004999999999999995, "BUILD") #Convert polygon to raster

#Create ML2 Global Shapefile and clean
print('Finding ML2 shapefiles')
file_path = directory + '\\*ML2.shp'
ML2files = glob.glob(file_path) #Get list of file paths to all ML2 Shapefiles
print('The list of ML2 shapefiles are ' + ' , '.join(ML2files))
ML2global_shapefile = 'Global_' + date[:4] + date[5:7] + "_ML2.shp"
print('Merging together ML2 shapefiles, and add HA2 value to ML2 value, and delete no data and national park')
arcpy.management.Merge(ML2files,ML2global_shapefile) #Merge together all ML2 shapefiles
arcpy.management.CalculateField(ML2global_shapefile, "ML2_adj", "!ML2!+!HA2!", "PYTHON3", '', "SHORT", "NO_ENFORCE_DOMAINS") #Add ML2 and HA2 together
arcpy.MakeTableView_management(ML2global_shapefile, "View") #Create a view from table called view
arcpy.SelectLayerByAttribute_management("View","NEW_SELECTION", 
                                        'ML2 IN (99, 88)') #Select values of 99 and 88 from global shapefiles
arcpy.DeleteRows_management("View") #Delete values of 99 and 88
#Create ML2 Raster
print('Converting ML2 Shapefile to Raster')
ML2_output_file= os.path.join(raster_folder, "Global_" + date[:4] + date[5:7] + "_ML2.tif")
arcpy.conversion.PolygonToRaster(ML2global_shapefile, "ML2_adj", ML2_output_file, "CELL_CENTER", "NONE", 0.004999999999999995, "BUILD") #Convert polygon to raster

print("Delete Files from " + directory)
files = os.listdir(directory)
for f in files:
    try:
        os.remove(f)
    except:
        pass

print("Script Complete")
