GOTO EndComment1
Options for WRSI Product are MaizeL (ee), GrainsL (el), GrainsB (ek), MaizeS (et), RangeS (e1) and RangeL (e2). Letter references the wrsi season, L = long/Gu, S = short/deyr, B = belg.
Two letter codes (i.e: ee, el, .etc) are the codes used by USGS in their file names.

There are six wrsi products in EA which have the following ranges: Maize - Long (Mar-Nov), Grains - Long (Apr-Nov), Grains - Belg (Mar-Sep), 
Maize - Short(Sep-Feb), Rangeland - Short (Sep-Jan), Rangeland - Long(Mar-Jul)

When running the zonal stats process, make sure to only run analysis for WRSI products which were updated prior to the last update of the GDHI. For instance, if you are in January the two 
Short rains products would need to be udpated. If you are April, the three long rains products and the belg rains data need to be updated. 

Each month has three dekads, data for month / dekad of interest needs to be posted USGS website prior to running script. Link to USGS website is below. 
website here: https://edcftp.cr.usgs.gov/project/fews/africa/east/dekadal/wrsi-chirps-etos/

Format for selecting file to run zonal statistics on is EE_YYYY_M_D. EE is the USGS product code, YYYY is the four digit year, M refers to the month, while D refers to the dekad with the month.

Add a : to mark when an analysis is not needed - this will result in command line ignoring that row.

:EndComment1

set PYTHON_PATH=C:\Users\bjanocha\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone\python.exe
set WRSI_FOLDER=C:\Users\bjanocha\OneDrive - Chemonics\05.WRSI
set YEAR=2023
set MONTH=06
set MAIZEL=ee_2023_6_3
set GRAINSL=el_2023_6_3
set GRAINSB=ek_2023_6_3
:set MAIZES=et_2023_6_3
:set RANGES=e1_2023_6_3
set RANGEL=e2_2023_6_3

:Run Zonal Statistics for each WRSI Product
"%PYTHON_PATH%" WRSI_Download_CHIRPS.py "%WRSI_FOLDER%" %YEAR% %MONTH% "%MAIZEL%"
"%PYTHON_PATH%" WRSI_Download_CHIRPS.py "%WRSI_FOLDER%" %YEAR% %MONTH% "%GRAINSL%"
"%PYTHON_PATH%" WRSI_Download_CHIRPS.py "%WRSI_FOLDER%" %YEAR% %MONTH% "%GRAINSB%"
:"%PYTHON_PATH%" WRSI_Download_CHIRPS.py "%WRSI_FOLDER%" %YEAR% %MONTH% "%MAIZES%"
:"%PYTHON_PATH%" WRSI_Download_CHIRPS.py "%WRSI_FOLDER%" %YEAR% %MONTH% "%RANGES%"
"%PYTHON_PATH%" WRSI_Download_CHIRPS.py "%WRSI_FOLDER%" %YEAR% %MONTH% "%RANGEL%"


:Run process for calcuating WRSI based crop production estimates based on WRSI data. 
"%PYTHON_PATH%" WRSI_Crop_Est_ET.py "%WRSI_FOLDER%" %YEAR% %MONTH%
"%PYTHON_PATH%" WRSI_Crop_Est_UGSOKE.py "%WRSI_FOLDER%" %YEAR% %MONTH%

pause