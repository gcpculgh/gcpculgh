#!/bin/bash

# 1. Enter the Django app directory
cd gcpcul

# 2. Compile and compress static assets perfectly
python manage.py collectstatic --noinput
python manage.py compress --force

echo "Static compilation complete."