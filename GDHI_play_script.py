# -*- coding: utf-8 -*-
"""
Created on Wed Feb  3 14:56:04 2021

@author: rbarad
"""
import os
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
import arcpy

arcpy.env.overwriteOutput = True

os.chdir(r'C:\Users\rbarad.CHEMONICS_HQ\Chemonics\Peter Thomas - GDHI\27. February Outlook Run\February2021')
arcpy.env.workspace=r'C:\Users\rbarad.CHEMONICS_HQ\OneDrive - Chemonics\Desktop\GDHI\GDHI_Results.gdb'

params= {'year'              :2021,
         'outlook'           :1,
         'input_featureclass':'SO_UG_KE_GDHI_Admin_LHZ',
         'output_featureclass':'GDHI_results_Feb2021'}

outlookquartertime = {}

outlookstart = {1: 1,
                2: 4,
                3: 10
                }

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

def create_quarter_variable_list():
    quarters=['Q1','Q2','Q3']
    variables = ['IPC_Max','IPC_Area','3plus','MT']
    quarter_variable_list = []
    for q in quarters:
        for v in variables:
            variable = q + "_" + v
            quarter_variable_list.append(variable)
    return quarter_variable_list

def generate_ranges(): #Generate months for each quarter
    print ("Gernerate date range for each quarter, based on selected outlook")
    start_date= datetime.date(params['year'], outlookstart[params['outlook']], 1) #Convert number representing month from outlook start to a date based on year, and start month of selected GDHI run
    outlookquartertime['Q1']= '(' + start_date.strftime("%b. %y") + ' - ' + (start_date + relativedelta(months=2)).strftime("%b. %y") + ')'
    outlookquartertime['Q2']= '(' + (start_date + relativedelta(months=3)).strftime("%b. %y") + ' - ' + (start_date + relativedelta(months=5)).strftime("%b. %y") + ')'
    outlookquartertime['Q3']= '(' + (start_date + relativedelta(months=6)).strftime("%b. %y") + ' - ' + (start_date + relativedelta(months=8)).strftime("%b. %y") + ')'
    
def create_results_featureclass():
    print("Create Featureclass for GDHI results")
    gdhi_shapes = os.path.join('in_memory',params["input_featureclass"]) #Save copy of GDHI Mapping units in memory
    arcpy.management.CopyFeatures(params["input_featureclass"], gdhi_shapes)
    #Convert GDHI results to a .csv and join results to featureclass, export featureclass to disk, delete .csv once complete
    results.to_csv('NATLIAS_results.csv')
    results_mapping= os.getcwd() + os.sep + "NATLIAS_results.csv"
    arcpy.JoinField_management(gdhi_shapes, 'FNID', results_mapping, 'FNID',fields_join)
    arcpy.management.CopyFeatures(gdhi_shapes, params['output_featureclass'])
    os.remove(results_mapping)

def set_aliases(): #Set aliases
    for field in fields_join:
        print("Update Alias for " + field)
        arcpy.AlterField_management(params['output_featureclass'], field, new_field_alias=alias_list[field])

results = pd.DataFrame(pd.read_excel('NatLIAS_res_summ.xlsx',sheet_name='Mapping',skiprows=1,nrows=280)) #Read results from GDHI into a Dataframe
fields_join = create_quarter_variable_list() + ['IPC_Max','IPC_Area_Max','IPC_Area_Avg','MT_Total','Total_pop','Kg_Per_capita'] #Create list of quarterly variables using two functions and add average variables to list
generate_ranges()
create_results_featureclass()
set_aliases()

#To do:
# 1) Read the year / outlook values directly from Excel so that they do not need to be updated by user
# 2) Create a layer from the resulting featureclass (Maybe just have an ArcGIS Pro Project which reads data layer)
# 3) Publish to ArcGIS Online / overwrite existing layer
# 4  Add LH Zone Names?

arcpy.Delete_management("in_memory") #Clear arcgis memory space 

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

IPC_Phase_Clean()
IPC_MT_Clean()

print("Script Complete")
