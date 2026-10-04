#!/usr/bin/env bash
set -o errexit

echo "--- 1. Installing dependencies ---"
pip install -r requirements.txt

echo "--- 2. Stripping AWS and Django-Summernote site-package bloat ---"
python3 -c "
import os, shutil

# Walk through the environment to find and clean heavy package assets
for root, dirs, files in os.walk('/'):
    # Strip unused AWS botocore data
    if 'botocore' in dirs:
        b_data = os.path.join(root, 'botocore', 'data')
        if os.path.exists(b_data):
            for item in os.listdir(b_data):
                if item not in ['s3', 's3control', 'sts', 'iam']:
                    shutil.rmtree(os.path.join(b_data, item), ignore_errors=True)
            print('Cleaned botocore data definitions.')

    # Strip heavy frontend static files bundled inside django-summernote
    if 'django_summernote' in dirs:
        ds_static = os.path.join(root, 'django_summernote', 'static')
        if os.path.exists(ds_static):
            shutil.rmtree(ds_static, ignore_errors=True)
            print('Stripped django_summernote static assets from backend bundle.')
"

echo "--- 3. Compiling Django static assets ---"
cd gcpcul
python manage.py collectstatic --noinput
python manage.py compress --force
cd ..

echo "--- 4. Cleaning temporary caches ---"
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
rm -rf gcpcul/db.sqlite3 gcpcul/media/ og-generator/

echo "--- Build preparation complete ---"