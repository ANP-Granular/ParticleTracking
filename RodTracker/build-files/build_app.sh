#!/usr/bin/env bash
# @echo off

BASEDIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Update version and build-date
cd $BASEDIR
VERSION=$(dunamai from any --bump)
DATE=$(date +'%d/%m/%Y')
printf "__version__ = '$VERSION'\n__date__ = '$DATE'\n" > ../src/RodTracker/_version.py

# (Re-)Generate documentation before application bundling
cd $BASEDIR
if [ ! -d $BASEDIR/../../docs/build/html ]
  then
    cd ../../docs
    make clean
    make html
fi

# TODO: build in a directory called VERSION
# Bundle the application
cd $BASEDIR
cd ..
if [ $# -eq 0 ]; then
    # build as one directory
    pyinstaller --distpath ./dist/linux --workpath ./build/linux \
      ./build-files/build_onedir.spec
  else
    if [ $1 == "-onefile" ]
      then
        # build as a single executable file
        pyinstaller ./build-files/build_onefile.spec
    fi
    if [ $1 == "-onedir" ]
      then
        # build as one directory
        pyinstaller --distpath ./dist/linux --workpath ./build/linux \
          ./build-files/build_onedir.spec
    fi
    if [[ $1 != "-onedir" && $1 != "-onefile" ]]
      then
        echo "Unknown parameter...Use -onefile or -onedir"
    fi
fi
