# -*- coding: utf-8 -*-
"""
Created on Wed Feb  3 14:56:04 2021
@author: rbarad

This scripts performs the following steps. Prior to running the script the GDHI for the current month should be run.

1) Update the ArcGIS Online Feature class, through the following steps:
    1) Extracts the results from the GDHI Results summary excel files and imports the results to Pandas Data frame
    2) Exports the pandas data frame to a .csv file, join the GDHI mapping feature class to the .csv and export the joined result
    3) Set appropriate Aliases for the feature class by looking up fields in the alias list
    4) Add feature class to a Pro project, and remove feature class from previous month
    5) Publish updated Pro map to AGOL and overwrite old results
    
2) Update the csv files used in the Power BI Dashboard:
    1) Get current outlook and year from Excel Interface file
    2) Create a dictionary with the time range associated with each analysis quarter based on the selected outlook run
    3) Flatten results using Pandas to create a flat file on population by Phase, by quarter for each area of analysis - export CSV results
    3) Flatten results using Pandas to create a flat file on MT needs by quarter for ach area of analysis - export CSV results

"""
import os
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
import arcpy
import openpyxl
from arcgis.gis import GIS

arcpy.env.overwriteOutput = True

#This is  the directory where the NATLIAS for the current month are saved
os.chdir(r'C:\Users\rbarad.CHEMONICS_HQ\Chemonics\FEWS NET Technical Team - 01.EA_Monthly_Runs\02.GDHI-tool\2021\04') #Path to GDHI Exceel files

params= {'input_featureclass':'SO_UG_KE_GDHI_Admin_LHZ', #Name of Feature class to join GDHI results to - must be stored in Pro Project GDB which is specified as the arcpy.env.workspace
         'month':4, #Current Month
         'year':2021, #Current Year
         'sharepoint_folder':r'C:\Users\rbarad.CHEMONICS_HQ\Chemonics\FEWS NET Technical Team - 01.EA_Monthly_Runs\01.SharePoint', #Location of Share Point folder containing ArcGIS Pro Project and Power BI Files
         'username':'rbarad_FEWSNET', #username for AGOL
         'password':'TYPE PASSWORD HERE'} #Password for AGOL

#Set the file path to the sharepoint folder, Project GDB, and Pro Project
sharepoint_folder = params['sharepoint_folder']
arcpy.env.workspace=os.path.join(sharepoint_folder,'GDHI_Results.gdb')
pro_project = os.path.join(sharepoint_folder,'GDHI_Results.aprx')

#Read results into a pandas dataframe
results = pd.DataFrame(pd.read_excel('NatLIAS_res_summ.xlsx',sheet_name='Mapping',skiprows=1,nrows=280)) #Read results from GDHI into a Dataframe

#Contains Aliases to assign to each column in the feature class
alias_list= {'Q1_IPC_Max': 'Q1 Max Indicative Household Phase','Q1_IPC_Area': 'Q1 Indicative Area Phase','Q1_3plus': 'Q1 Pop in IPC Phase 3+','Q1_MT': 'Q1 - Metric Tons of aid',
             'Q2_IPC_Max': 'Q2 Max Indicative Household Phase','Q2_IPC_Area': 'Q2 Indicative Area Phase','Q2_3plus': 'Q2 Pop in IPC Phase 3+','Q2_MT': 'Q2 - Metric Tons of aid',
             'Q3_IPC_Max': 'Q3 Max Indicative Household Phase','Q3_IPC_Area': 'Q3 Indicative Area Phase','Q3_3plus': 'Q3 Pop in IPC Phase 3+', 'Q3_MT': 'Q3 - Metric Tons of aid',
             'IPC_Max': 'Highest Indicative Household Phase','IPC_Area_Max':'Highest Indicative Area Phase', 'IPC_Area_Avg': 'Average Indicative Phase','MT_Total': 'Total Metric tons (Q1 - Q3)',
             'Total_pop':'Total Population','Kg_Per_capita':'Kilograms per capita'}

def create_quarter_IPC_list(): #Creates a list of collumns names for the combinations of IPC Phases and quarter (i.e: Q1_IPC1, Q1_IPC2, Q1_IPC3, Q1_IPC4, Q1_IPC5, Q2_IPC1, etc.) 
    quarters=['Q1','Q2','Q3']
    quarters_phase_list = []
    IPC_Phase = range(1,6)
    for q in quarters:
        for p in IPC_Phase:
            quarter_phase = q + '_IPC' + str(p)
            quarters_phase_list.append(quarter_phase)
    return quarters_phase_list

def create_quarter_variable_list(): #Create list of data column names for each quarter - includes MT per quarter, Area Phase Clasification, Highest Phase Classification, and Metric Tons (MT) 
    quarters=['Q1','Q2','Q3']
    fields = ['IPC_Max','IPC_Area','3plus','MT']
    quarter_field_list = []
    for q in quarters:
        for f in fields:
            field = q + "_" + f
            quarter_field_list.append(field)
    return quarter_field_list

def set_output_feature_class_name(): #Set name of the feature class output which is written to the Project GDB - include date of analysis in file name
    month_name = datetime.date(params['year'], params['month'], 1).strftime('%Y_%m') #Convert month and year of analysis to a date, and than translate to the three letter month name 
    output_featureclass = 'GDHI_results_' + month_name
    return output_featureclass
    
def create_results_featureclass():
    print("Create Featureclass for GDHI results...")
    #Save copy of GDHI Mapping units in memory
    gdhi_shapes = os.path.join('in_memory',params["input_featureclass"]) 
    arcpy.management.CopyFeatures(params["input_featureclass"], gdhi_shapes)
    #Convert GDHI results to a .csv and join results to featureclass, export featureclass to disk, delete .csv once complete
    results.to_csv('NATLIAS_results.csv')
    results_mapping= os.getcwd() + os.sep + "NATLIAS_results.csv"
    arcpy.JoinField_management(gdhi_shapes, 'FNID', results_mapping, 'FNID',fields_join)
    arcpy.management.CopyFeatures(gdhi_shapes, output)
    os.remove(results_mapping)

def set_aliases(): #Set aliases
    for field in fields_join:
        print("Update Alias for " + field)
        arcpy.AlterField_management(output, field, new_field_alias=alias_list[field])

#Create featureclass for ESRI story map using defined functions
fields_join = create_quarter_variable_list() + ['IPC_Max','IPC_Area_Max','IPC_Area_Avg','MT_Total','Total_pop','Kg_Per_capita'] #Create list of quarterly data fields using function and add average variables to list
output = set_output_feature_class_name()
create_results_featureclass()
set_aliases()

#Create variables for Pro Project and Map in Pro Project
aprx = arcpy.mp.ArcGISProject(pro_project)
aprxMap = aprx.listMaps("Map")[0] 

def update_pro_project():
    #Add new resuls Featureclass to the ArcGIS Pro Project - rename layer to GDHI_Results, but first remove old GDHI results layer from map so that map only includes one layer.
    print("Update Pro Project...")
    lyr_path = os.path.join(arcpy.env.workspace,output)
    removeLyr = aprxMap.listLayers('GDHI_results')[0] #Remove old existing layer from map.
    aprxMap.removeLayer(removeLyr)
    aprxMap.addDataFromPath(lyr_path)
    lyr = aprxMap.listLayers()[0] #Select first and only layer in map
    lyr.name = 'GDHI_results' #Rename selected layer to 'GDHI_results'
    aprx.save()
    print("Pro Project Updated")

def update_AGOL():
    # Set sharing draft and service definition file names
    service = "GDHI_results"
    sddraft_filename = os.path.join(sharepoint_folder, service + ".sddraft")
    sd_filename = os.path.join(sharepoint_folder, service + ".sd")
    # Create FeatureSharingDraft and set service properties
    print("Create Sharing Draft and Service Defintion Files...")
    sharing_draft = aprxMap.getWebLayerSharingDraft("HOSTING_SERVER", "FEATURE", service)
    sharing_draft.summary = "Results of the GDHI for " + datetime.date(params['year'], params['month'], 1).strftime('%B %Y')
    sharing_draft.overwriteExistingService = True
    sharing_draft.portalFolder = '01. GDHI'
    # Create Service Definition Draft file and service definition
    sharing_draft.exportToSDDraft(sddraft_filename)
    arcpy.StageService_server(sddraft_filename, sd_filename)
    #Sign in to ArcGIS Online
    print("Sign in to ArcGIS Online")
    gis = GIS('https://www.arcgis.com', params['username'], params['password'])
    # Find the Service definition, update it, publish /w overwrite and set sharing and metadata
    print("Search for original SD on portal…")
    sdItem = gis.content.search(query="title:"+ service + " AND owner: " + 'rbarad_FEWSNET', item_type="Service Definition")[0]
    print("Found SD: {}, ID: {} Uploading and overwriting…".format(sdItem.title, sdItem.id))
    sdItem.update(data=sd_filename)
    print("Overwriting existing feature service…")
    fs = sdItem.publish(overwrite=True)
    print("Finished updating: {} – ID: {}".format(fs.title, fs.id))

#Update Pro project and publish feature class to AGOL.
update_pro_project()
update_AGOL()

arcpy.Delete_management("in_memory") #Clear arcgis memory space

#Rest of script creates csv files which are used in Power Bi

outlookquartertime = {}

outlookstart = {1: 1,
                2: 4,
                3: 10
                }

def get_outlook_year_from_Excel(): #Get the outlook and year of analysis from the SO, UG, KE GDHI file.
    book = openpyxl.load_workbook('NatLIAS_interface.xlsm')
    sheet = book.active
    year = sheet['E9'].value
    outlook = sheet['E7'].value
    return[year,outlook]

def generate_ranges(): #Generate month ranges for each quarter and write results to a python dictionary, subsequently used in IPC_Phase_Clean() and IPC_MT_Clean() functions to get the month ranges for eqch quarter
    print ("Gernerate date range for each quarter, based on selected outlook")
    date = get_outlook_year_from_Excel()
    start_date= datetime.date(date[0], outlookstart[date[1]], 1) #Convert number representing month from outlook start to a date based on year, and start month of selected GDHI run
    outlookquartertime['Q1']= '(' + start_date.strftime("%b. %y") + ' - ' + (start_date + relativedelta(months=2)).strftime("%b. %y") + ')'
    outlookquartertime['Q2']= '(' + (start_date + relativedelta(months=3)).strftime("%b. %y") + ' - ' + (start_date + relativedelta(months=5)).strftime("%b. %y") + ')'
    outlookquartertime['Q3']= '(' + (start_date + relativedelta(months=6)).strftime("%b. %y") + ' - ' + (start_date + relativedelta(months=8)).strftime("%b. %y") + ')'

def IPC_Phase_Clean(): #Flatten to create a file on population by Phase, per quarter
    print("Create File for IPC Phase by Quarter")
    results_org = results.melt(id_vars=['FNID','COUNTRY','Admin1','Admin2','Admin3','LH Zone','Total_pop'],value_vars=create_quarter_IPC_list(),value_name='Pop',var_name='Quarter_Phase')
    results_org['Quarter'] = results_org['Quarter_Phase'].str.split("_",n = 1, expand = True)[0]
    results_org['Phase'] = results_org['Quarter_Phase'].str.split("_",n = 1, expand = True)[1]
    results_org['Quarter'] = results_org['Quarter'] + ' ' + results_org['Quarter'].map(outlookquartertime)
    results_org.drop(labels='Quarter_Phase',axis=1,inplace=True)
    results_org.sort_values(['COUNTRY','Admin1','Admin2','Admin3','LH Zone','Quarter','Phase'],inplace=True)
    results_org.to_csv('IPC_Phase.csv')

def IPC_MT_Clean(): #Flatten to create a file on MT by quarter
    print("Create File for MT Needs by Quarter")
    results_org_MT = results.melt(id_vars=['FNID','COUNTRY','Admin1','Admin2','Admin3','LH Zone','Total_pop'],value_vars=['Q1_MT','Q2_MT','Q3_MT'],value_name='MT',var_name='Quarter_MT')
    results_org_MT['Quarter'] = results_org_MT['Quarter_MT'].str.split("_",n = 1, expand = True)[0]
    results_org_MT['Quarter_detail'] = results_org_MT['Quarter'] + ' ' + results_org_MT['Quarter'].map(outlookquartertime)
    results_org_MT.drop(labels='Quarter_MT',axis=1,inplace=True)
    results_org_MT.sort_values(['COUNTRY','Admin1','Admin2','Admin3','LH Zone','Quarter',],inplace=True)
    results_org_MT.to_csv('MT_Needs.csv')

#Create csv files for PowerBI - save to Sharepoint folder
os.chdir(sharepoint_folder)

generate_ranges()
IPC_Phase_Clean()
IPC_MT_Clean()

print("Script Complete")
