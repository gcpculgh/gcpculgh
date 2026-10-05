#!/usr/bin/env bash
set -o errexit

echo "--- Running compress ---"
cd gcpcul
python manage.py compress --force
cd ..
echo "--- Done ---"   