#!/usr/bin/env bash
# @echo off

BASEDIR=$(dirname "$0")
cd $BASEDIR
cd ..

if [ $# -eq 0 ]; then
    # build as one directory
    echo "The bundling as a directory process is currently broken."
    echo "Please use the -onefile option."
    # pyinstaller ./build-files/build_onedir.spec
  else
    if [ $1 == "-onefile" ]
      then
        # build as a single executable file
        pyinstaller ./build-files/build_onefile.spec
    fi
    if [ $1 == "-onedir" ]
      then
        # build as one directory
        echo "The bundling as a directory process is currently broken."
        echo "Please use the -onefile option."
        # pyinstaller ./build-files/build_onedir.spec
    fi
    if [[ $1 != "-onedir" && $1 != "-onefile" ]]
      then
        echo "Unknown parameter...Use -onefile or -onedir"
    fi
fi