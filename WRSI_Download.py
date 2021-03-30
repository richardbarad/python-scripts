#-------------------------------------------------------------------------------
# Name:       WRSI Zonal Statistics
# Purpose:    Download selected WRSI file from USGS website, unzip it, and summarize WRSI data by adminstration units of interest using zonal statistics tools. Requires Arcpy and spatial analayst extension to run.
#
# Author:      Richard Barad, FEWS NET
#
# Created:     18/06/2020
# Copyright:   (c) rbarad / FEWS NET 2020-2021
# Licence:    None
#-------------------------------------------------------------------------------

import arcpy
import os
import requests
import zipfile

arcpy.env.overwriteOutput = True #Allow file overwrites

arcpy.CheckOutExtension("Spatial") #Checkout Spatial Analyst Extention - requires access to a Spatial Analyst Extension to run 

params ={'workspace':r'C:\Users\rbarad.CHEMONICS_HQ\OneDrive - Chemonics\Desktop\GDHI\WRSI Data\20210326',
         'year':2021, #Options are 2001 - Present
         'month':2, #Options are 1 - 12, make sure you select a month which is appropriate to the product you select
         'dekad':3, #Options are 1 - 3 (three dekads in each month)
         'product':'Maize - Short Rains (Sep-Feb)',
         #The options for the product are Maize - Long Rains (Mar-Nov), Grains - Long Rains (Apr-Nov), Grains - Belg (Mar-Sep), Maize - Short Rains (Sep-Feb), Rangeland - Short Rains (Sep-Jan), Rangeland - Long Rains (Mar-Jul)
         'inpoly': r'C:\Users\rbarad.CHEMONICS_HQ\OneDrive - Chemonics\Desktop\GDHI\WRSI Data\WRSI_Data.gdb\GDHI_Admin_Units_test', #File path to a GIS shapefile or feature class to use for zonal statistics analysis
         'baseurl':r'https://edcftp.cr.usgs.gov/project/fews/dekadal/africa_east' #Url to the location of the WRSI data on USGS FTP
         }

variables ={} #set set_url_filenames() & set_other_variables functions write to this dictionary

#Set ArcGIS Enviroment to workspace params and then set active directory to the workspace - downloaded files will be saved in selected location and outputs of ArcGIS processing will also be saved there
arcpy.env.workspace = params['workspace']
dir=arcpy.env.workspace
os.chdir(dir)

product=params['product'] #Get product into a string variable to be able to reference it more easily in additional code.
inpoly=params['inpoly'] #Make inpoly more accessible

def set_url_filenames(): #Create the url for downloading the data from the USGS website
    print('Creating url and file name variables based on selected product')
    #Covert year to a two digit number as text
    year_two_dig=params['year']-2000
    if year_two_dig < 10:
        url_year = "0" + str(year_two_dig)
    else:
        url_year = str(year_two_dig)
    #Convert dekad of month to dekad on an annual 1-36 scale
    dekad_m = (params['month'] - 1) * 3 + params['dekad']
    if dekad_m < 10:
        url_dekad = '0' + str(dekad_m)
    else:
        url_dekad = str(dekad_m)
    if product == 'Maize - Long Rains (Mar-Nov)':
        url_product = 'ee'
    elif product == 'Grains - Long Rains (Apr-Nov)':
        url_product = 'el'
    elif product == 'Grains - Belg (Mar-Sep)':
        url_product = 'ek'
    elif product == 'Rangeland - Long Rains (Mar-Jul)':
        url_product = 'e2'
    elif product == 'Rangeland - Short Rains (Sep-Jan)':
        url_product = 'e1'
    elif product == 'Maize - Short Rains (Sep-Feb)':
        url_product = 'et'
    #Set variables - write to variables dictionary, variables used latter in other functions.
    variables['url_year'] = url_year
    variables['zipfilename'] = 'w' + url_year + url_dekad + url_product + '.zip'
    variables['filename']= 'w' + url_year + url_dekad + 'eo' #eo is name of the file for the WRSI extended, zipped file download includes multiple tiff files for different WRSI products.

def set_other_variables(): #extract the name of the season and name of the crop from the product parameter as new variables - save to variables dictionary. Variables used later in other functions.
    print('Setting variables based on selected product')
    season_char_start= product.find('-') + 2
    season_char_end=season_char_start + 4
    variables['season'] = product[season_char_start:season_char_end]
    crop_char_end=product.find('-') - 1
    variables['crop'] = product[:crop_char_end]
    variables['cropcode']=variables['crop'][0:1]

def download_unzip_data(): #Download the WRSI File for the relevant year and save it to the workspace
    zipfilename = variables['zipfilename']
    url = params['baseurl'] + '/' + zipfilename
    print ("Downloading WRSI file at" + url)
    WRSI_download = requests.get(url)
    print ("Download Status code: " + str(WRSI_download.status_code)) #make sure status code is not 404, if 404 the file likely does not exist on USGS website and script will not run in full
    open(zipfilename,'wb').write(WRSI_download.content)
    print ("Extracting WRSI zipped file")
    with zipfile.ZipFile(zipfilename,'r') as zipobj:
        zipobj.extractall()
    print ("Zip file extracted")

set_url_filenames()
set_other_variables()
download_unzip_data()

def reclass_raster(): #Reclass raster, set no start values to 0 and yet to start values to Null (no data)
    tifilename= variables['filename'] + '.tif'
    print ("Reclassifying " + str(params["year"]) +" "+ product + " raster - set no start values to 0")
    outCon = arcpy.sa.Con(tifilename,0,tifilename,"value=253")
    print ("Reclassifying " + str(params["year"]) +" "+ product + " raster - set yet to start values to null")
    outSetNull = arcpy.sa.SetNull(outCon, outCon, "value=254")
    return outSetNull

def zonal_stats_export_to_excel():
    reclassed_raster = reclass_raster()
    #Run Zonal statistics on reclassified raster
    print ("Running Zonal Statistics for " + str(params["year"]) + " "+ product + " exported in memory")
    outtable= os.path.join('in_memory', variables['filename'])
    arcpy.sa.ZonalStatisticsAsTable(inpoly,"FNID",reclassed_raster,outtable,"DATA","MEAN")
    print ("Zonal Statistcs for " + str(params['year']) + " "+ product + " exported in memory")
    #Add a field to the zonal stats results, set euqal to MEAN from zonal stats operation, and append field to the inpoly. 
    field_name = variables['season'] + variables['cropcode'] + str(variables['url_year']) + str(params['month']) + str(params['dekad'])
    alias = str(params['year']) + ' ' + str(params['month']) + ' ' + str(params['dekad']) + ' ' +variables['season'].title() + ' Rains ' + variables['crop'].title() + ' WRSI'
    print ("Adding field to the feature class and calculating value for " + variables['season'] + " Rains " + str(params['year']))
    arcpy.AddField_management(outtable,field_name,"FLOAT",field_alias=alias)
    arcpy.CalculateField_management(outtable,field_name,"!MEAN!","PYTHON")
    arcpy.JoinField_management(inpoly,"FNID",outtable,"FNID",field_name)
    #Export data to excel
    excel_name = 'WRSI_' + variables['season'] + '_' + str(params['year']) + '_' + str(params['month']) + '_' + str(params['dekad']) + '_' + variables['crop'] + '.xlsx' #Export data to excel
    arcpy.TableToExcel_conversion(inpoly,excel_name,"ALIAS")
    #Delete average field from input featureclass
    arcpy.DeleteField_management(inpoly,[field_name]) #Delete average field from input featureclass

zonal_stats_export_to_excel()

print ("Script complete")