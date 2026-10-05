#!/usr/bin/env bash
set -o errexit

echo "--- 1. Compiling Django static assets ---"
cd gcpcul
python manage.py collectstatic --noinput --clear
python manage.py compress --force
cd ..

echo "--- 2. Surgically stripping bloat from Vercel site-packages ---"
python3 -c "
import os, shutil

# 1. Obliterate Botocore data schemas (Saves ~50MB)
try:
    import botocore
    b_data = os.path.join(os.path.dirname(botocore.__file__), 'data')
    if os.path.exists(b_data):
        for item in os.listdir(b_data):
            if item not in ['s3', 's3control', 'sts', 'iam']:
                shutil.rmtree(os.path.join(b_data, item), ignore_errors=True)
except ImportError:
    pass

# 2. Obliterate Summernote static files (Saves ~15MB)
try:
    import django_summernote
    s_static = os.path.join(os.path.dirname(django_summernote.__file__), 'static')
    if os.path.exists(s_static):
        shutil.rmtree(s_static, ignore_errors=True)
except ImportError:
    pass
"

echo "--- 3. Cleaning media and temporary caches ---"
rm -rf gcpcul/media/
rm -rf og-generator/
find . -type d -name \"__pycache__\" -exec rm -rf {} +
find . -type f -name \"*.pyc\" -delete

echo "--- Build preparation complete ---"