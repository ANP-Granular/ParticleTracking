#!/usr/bin/env bash
# @echo off

BASEDIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# (Re-)Generate documentation before application bundling
cd $BASEDIR
cd ../../docs
make clean
make html

# Bundle the application
cd $BASEDIR
cd ..
if [ $# -eq 0 ]; then
    # build as one directory
    pyinstaller ./build-files/build_onedir.spec
  else
    if [ $1 == "-onefile" ]
      then
        # build as a single executable file
        pyinstaller ./build-files/build_onefile.spec
    fi
    if [ $1 == "-onedir" ]
      then
        # build as one directory
        pyinstaller ./build-files/build_onedir.spec
    fi
    if [[ $1 != "-onedir" && $1 != "-onefile" ]]
      then
        echo "Unknown parameter...Use -onefile or -onedir"
    fi
fi