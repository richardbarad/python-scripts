GOTO EndComment1
Options for WRSI Product are MaizeL (ee), GrainsL (el), GrainsB (ek), MaizeS (et), RangeS (e1) and RangeL (e2). Letter references the wrsi season, L = long/Gu, S = short/deyr, B = belg.
Two letter codes are the codes used by USGS in their file names.

There are six wrsi products in EA which have the following ranges: Maize - Long (Mar-Nov), Grains - Long (Apr-Nov), Grains - Belg (Mar-Sep), 
Maize - Short(Sep-Feb), Rangeland - Short (Sep-Jan), Rangeland - Long(Mar-Jul)

When running the zonal stats process, make sure to only include WRSI products which were updated prior to the last update of the GDHI. For instance, if you are in January the two 
Short rains products would need to be udpated. Each month has three dekads, data for month / dekad of interest needs to be posted USGS website prior to running script - link to 
website here: https://edcftp.cr.usgs.gov/project/fews/africa/east/dekadal/wrsi-chirps-etos/

Format for selecting file to run zonal statistics on is PRODUCT_YEAR_MONTH_DEKAD. Add a : to mark when an analysis is not needed - this will result in command line ignoring that row.

:EndComment1

set WRSI_FOLDER=C:\Users\rbarad\OneDrive - Chemonics\10.GDHI\01.EA_Monthly_Runs\05.WRSI
set YEAR=2022
set MONTH=2
:set MAIZEL=MaizeL_2021_11_3
:set GRAINSL=GrainsL_2021_11_3
:set GRAINSB=GrainsB_2021_9_3
set MAIZES=MaizeS_2022_02_2
set RANGES=RangeS_2022_01_3
:set RANGEL=RangeL_2021_07_3

:Run Zonal Statistics for each WRSI Product
:"C:\Users\rbarad\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone\python.exe" WRSI_Download_CHIRPS.py "%WRSI_FOLDER%" %YEAR% %MONTH% "%MAIZEL%"
:"C:\Users\rbarad\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone\python.exe" WRSI_Download_CHIRPS.py "%WRSI_FOLDER%" %YEAR% %MONTH% "%GRAINSL%"
:"C:\Users\rbarad\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone\python.exe" WRSI_Download_CHIRPS.py "%WRSI_FOLDER%" %YEAR% %MONTH% "%GRAINSB%"
"C:\Users\rbarad\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone\python.exe" WRSI_Download_CHIRPS.py "%WRSI_FOLDER%" %YEAR% %MONTH% "%MAIZES%"
"C:\Users\rbarad\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone\python.exe" WRSI_Download_CHIRPS.py "%WRSI_FOLDER%" %YEAR% %MONTH% "%RANGES%"
:"C:\Users\rbarad\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone\python.exe" WRSI_Download_CHIRPS.py "%WRSI_FOLDER%" %YEAR% %MONTH% "%RANGEL%"


:Run process for calcuating WRSI based crop production estimates based on WRSI data. 
"C:\Users\rbarad\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone\python.exe" WRSI_Crop_Est_ET.py "%WRSI_FOLDER%" %YEAR% %MONTH%
"C:\Users\rbarad\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone\python.exe" WRSI_Crop_Est_UGSOKE.py "%WRSI_FOLDER%" %YEAR% %MONTH%

pause