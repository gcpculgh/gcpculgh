#!/usr/bin/env bash
set -o errexit

echo "--- 1. Installing dependencies ---"
pip install -r requirements.txt

echo "--- 2. Executing surgical AWS bloat removal ---"
# Find where botocore was installed and strip heavy unused service data
python3 -c "
import os, shutil
for root, dirs, files in os.walk('/'):
    if 'botocore' in dirs:
        botocore_data = os.path.join(root, 'botocore', 'data')
        if os.path.exists(botocore_data):
            print('Found botocore data at:', botocore_data)
            for item in os.listdir(botocore_data):
                if item not in ['s3', 's3control', 'sts', 'iam']:
                    shutil.rmtree(os.path.join(botocore_data, item), ignore_errors=True)
            print('Stripped unused AWS service definitions from botocore.')
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