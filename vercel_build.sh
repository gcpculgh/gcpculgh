#!/usr/bin/env bash
set -o errexit

echo "--- 0. Flushing stale virtual environment cruft ---"
rm -rf .vercel/python/

echo "--- 1. Installing dependencies cleanly ---"
pip install -r requirements.txt

echo "--- 2. Stripping AWS site-package bloat ---"
python3 -c "
import os, shutil
for root, dirs, files in os.walk('/'):
    if 'botocore' in dirs:
        b_data = os.path.join(root, 'botocore', 'data')
        if os.path.exists(b_data):
            for item in os.listdir(b_data):
                if item not in ['s3', 's3control', 'sts', 'iam']:
                    shutil.rmtree(os.path.join(b_data, item), ignore_errors=True)
            print('Cleaned botocore data definitions.')
"

echo "--- 3. Compiling Django static assets ---"
cd gcpcul
python manage.py collectstatic --noinput
python manage.py compress --force
cd ..

echo "--- 4. Nuking staticfiles and media from disk so Vercel doesn't zip them ---"
rm -rf gcpcul/staticfiles/
rm -rf gcpcul/media/
rm -rf og-generator/

echo "--- 5. Cleaning temporary caches ---"
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

echo "--- Build preparation complete ---"