rem ********************************************
rem Customize this according to your environment
rem ********************************************

rem Zope environment settings as in http://your.zope.instance/Control_Panel
rem ***********************************************************************
set INSTANCE_HOME=C:\zope\z270i1
set SOFTWARE_HOME=C:\zope\z270core\lib\python

rem The Python engine for Zope may not be the system default Python engine
rem **********************************************************************
set PYTHON=C:\Python23\python.exe

rem ZMySQLDA connection string to your test MySQL database.
rem Refer ZMySQLDA documentation for connection string syntax.
rem The MySQL user must have "create table" granted.
rem **********************************************************
set DBCONNECTS=-test_bdn@localhost user password
