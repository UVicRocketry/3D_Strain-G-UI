@echo off
:: Used to setup python virtual envrioment and install dependancies
Echo Installing virtualenv
python -m pip install --user virtualenv

Echo Creating Virtual Env
python -m venv env

Echo Activating Enviroment
cd env\Scripts
START powershell.exe -NoExit ".\activate.ps1"; cd..; cd..;"pip install -r requirements.txt"

Echo Done
PAUSE
