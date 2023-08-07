# -*- coding: utf-8 -*-
"""
Created on Thu May 19 15:23:17 2022

This script will:
1) Identify all the raster file which include the pattern specified as the wildcard
2) Calculate zonal statistics for all rasters which match the wildcard name pattern
3) Append zonal statistics to global feature class of all FEWS NET Food Insecurity Mapping units (if column already exists, values will be updated). If column does not exist, a new column will be added.
4) Export data to Excel in desired location

@author: rbarad
"""

import arcpy
import os                                                                             
import glob

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True #Allow file overwrites

featureclass = r'M:\EW Evaluation Maps\Global_ipc_rasters\Historic_IPC_Data.gdb\FEWSNET_Historical_ML2' #Path to featureclass/shapefile containing zonal stats
raster_folder = r'M:\EW Evaluation Maps\Global_ipc_rasters' #path to folder containing rasters

filename='Global_202302_ML2.tif' #Filename to determine which file rasters zonal stats are calculated for

output=r'C:\Users\rbarad\Desktop\FEWS_NET_ML2.xlsx' #Name of output file - should be .xlsx format

arcpy.env.workspace = raster_folder
os.chdir(raster_folder)                                                             

forecast=featureclass[-3:] 

rasters = glob.glob(filename)

for r in rasters:
    year=r[7:11]
    month=r[11:13]
    print('Analyze ' + forecast + ' Raster for ' + month +' ' + year)
    output_name = 'output_' + year + month
    outtable= os.path.join('memory',output_name)
    arcpy.sa.ZonalStatisticsAsTable(featureclass, 'FNID', r , outtable,'DATA','MEAN')
    table_join = arcpy.management.AddJoin(featureclass, "FNID", outtable, "FNID", "KEEP_ALL") #Create join between layer and results of zonal statistics
    py_expr= '!' + output_name + '.MEAN!'
    join_field = forecast +'_' + year + month
    arcpy.management.CalculateField(table_join,join_field,py_expr,"PYTHON3",'',"FLOAT")

arcpy.conversion.TableToExcel(featureclass, output)

print('Script Complete')
                                                     





