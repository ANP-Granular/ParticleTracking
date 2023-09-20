#!/usr/bin/env bash
# @echo off

BASEDIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $BASEDIR

# Preparations
echo "Preparing files..."
rm -r ../dist/unix/RodTracker-Setup
mkdir -p ../dist/unix/RodTracker-Setup
cp -r ../dist/unix/RodTracker.app ../dist/unix/RodTracker-Setup
test -f ../dist/unix/RodTracker-Setup.dmg && rm ../dist/unix/RodTracker-Setup.dmg

create-dmg \
  --volname "RodTracker" \
  --icon-size 100 \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon "RodTracker.app" 175 120 \
  --app-drop-link 425 120 \
  --eula "../LICENSE" \
  --no-internet-enable \
  "../dist/unix/RodTracker-Setup.dmg" \
  "../dist/unix/RodTracker-Setup"

# Clean up
rm -r ../dist/unix/RodTracker-Setup