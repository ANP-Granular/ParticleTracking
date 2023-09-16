#!/usr/bin/env bash
# @echo off

MAIN_DIR="RodTracker-Setup"

mkdir -p ../dist/unix/$MAIN_DIR/DEBIAN
cp control ../dist/unix/$MAIN_DIR/DEBIAN
cp ../LICENSE ../dist/unix/$MAIN_DIR/DEBIAN
mv ../dist/unix/$MAIN_DIR/DEBIAN/LICENSE ../dist/unix/$MAIN_DIR/DEBIAN/copyright

mkdir -p ../dist/unix/$MAIN_DIR/usr/share/applications
cp RodTracker.desktop ../dist/unix/$MAIN_DIR/usr/share/applications

mkdir -p ../dist/unix/$MAIN_DIR/usr/local
cp --recursive ../dist/unix/RodTracker ../dist/unix/$MAIN_DIR/usr/local

echo "Information: The next step can take >15 min ..."
dpkg-deb --verbose --build ../dist/unix/$MAIN_DIR
