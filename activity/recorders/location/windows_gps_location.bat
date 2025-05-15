:: @echo off
:: Change to the directory containing your script and virtual environment
cd /d C:\Users\TonyMason\source\repos\indaleko\main

:: Activate the virtual environment
call .venv-win32-python3.12\Scripts\activate.bat

:: change to script location
pushd activity\recorders\location

:: Run your Python script
python windows_gps_location.py

:: return to root directory
popd

:: Deactivate the virtual environment (optional)
call .venv-win32-python3.12\Scripts\deactivate.bat

exit
