#!/usr/bin/env bash
# @echo off

MAIN_DIR="RodTracker-Setup"

mkdir -p ../dist/linux/$MAIN_DIR/DEBIAN
cp control ../dist/linux/$MAIN_DIR/DEBIAN
cp ../LICENSE ../dist/linux/$MAIN_DIR/DEBIAN
mv ../dist/linux/$MAIN_DIR/DEBIAN/LICENSE ../dist/linux/$MAIN_DIR/DEBIAN/copyright

mkdir -p ../dist/linux/$MAIN_DIR/usr/share/applications
cp RodTracker.desktop ../dist/linux/$MAIN_DIR/usr/share/applications

mkdir -p ../dist/linux/$MAIN_DIR/usr/local
cp --recursive ../dist/linux/RodTracker ../dist/linux/$MAIN_DIR/usr/local

echo "Information: The next step can take >15 min ..."
dpkg-deb --verbose --build ../dist/linux/$MAIN_DIR
