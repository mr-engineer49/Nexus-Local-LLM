#!/usr/bin/env bash
set -e

echo "Checking Python..."
python3 --version

echo "Installing dependencies..."
pip3 install -q PyQt6 psutil

echo "Launching NEXUS..."
python3 run_nexus.py
echo "NEXUS launched successfully!"
