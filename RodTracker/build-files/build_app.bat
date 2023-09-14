@echo off
SET basedir=%~dp0

@REM (Re-)Generate documentation before application bundling
cd %basedir%
cd ..\..\docs
call make clean
call make html

@REM Bundle the application
cd %basedir%
cd ..
if [%1]==[] goto onedir
if %1==-onefile goto onefile
if %1==-onedir goto onedir
goto unknown

:onedir
pyinstaller --distpath .\dist\windows --workpath .\build\windows ^
    .\build-files\build_onedir.spec
goto eof

:onefile
pyinstaller .\build-files\build_onefile.spec
goto eof

:unknown
echo Unkown parameter...Use -onefile or -onedir

:eof
