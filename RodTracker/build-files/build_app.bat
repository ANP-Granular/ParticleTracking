@echo off
cd %~p0
cd ..
if [%1]==[] goto onedir
if %1==-onefile goto onefile 
if %1==-onedir goto onedir
goto unknown

:onedir
pyinstaller .\build-files\build_onedir.spec
goto eof

:onefile
pyinstaller .\build-files\build_onefile.spec
goto eof

:unknown
echo Unkown parameter...Use -onefile or -onedir

:eof