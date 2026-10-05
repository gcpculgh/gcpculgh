#!/usr/bin/env bash
set -o errexit

cd gcpcul
python manage.py collectstatic --noinput --clear
python manage.py compress --force
cd ..
echo "--- Done ---"   