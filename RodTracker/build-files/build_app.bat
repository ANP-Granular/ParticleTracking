@echo off
SET basedir=%~dp0

@REM Update version and build-date
cd %basedir%
FOR /F "tokens=*" %%F IN ('"dunamai from git --bump"') DO SET version=%%F
for /f "tokens=1-4 delims=/" %%i in ("%date%") do (
    set day=%%i
    set month=%%j
    set year=%%k
)
set datestr=%day%.%month%.%year%
> ..\src\RodTracker\_version.py (
    echo __version__ = "%version%"
    echo __date__ = "%datestr%"
)

@REM (Re-)Generate documentation before application bundling
cd %basedir%
if not exist ..\..\docs\build\html\ (
    cd ..\..\docs
    call make clean
    call make html
)

@REM TODO: build in a directory called VERSION
@REM Bundle the application
cd %basedir%
cd ..
python build-files\build_version_info.py

pyinstaller --distpath .\dist\windows --workpath .\build\windows ^
    .\build-files\build_onedir.spec
