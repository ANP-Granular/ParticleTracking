#!/usr/bin/env bash
# @echo off

BASEDIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Update version and build-date
cd $BASEDIR
VERSION=$(dunamai from any --bump)
DATE=$(date +'%d.%m.%Y')
printf "__version__ = '$VERSION'\n__date__ = '$DATE'\n" > \
  ../src/RodTracker/_version.py

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
pyinstaller --distpath ./dist/unix --workpath ./build/unix \
  ./build-files/build_onedir.spec
