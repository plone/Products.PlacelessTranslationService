@echo off
rem Executes a test Python script
rem USAGE:
rem runtest[.bat] testXXX.py
call environ.bat
"%PYTHON%" %1
