#!/usr/bin/env bash
set -o errexit

echo "--- 1. Compiling Django static assets ---"
cd gcpcul
python manage.py collectstatic --noinput --clear
python manage.py compress --force
cd ..

echo "--- 2. Stripping AWS and Summernote bloat ---"
python3 -c "
import os, shutil
for root, dirs, files in os.walk('/'):
    if 'botocore' in dirs:
        b_data = os.path.join(root, 'botocore', 'data')
        if os.path.exists(b_data):
            for item in os.listdir(b_data):
                if item not in ['s3', 's3control', 'sts', 'iam']:
                    shutil.rmtree(os.path.join(b_data, item), ignore_errors=True)
"
# Target only the heavy summernote directory instead of nuking all staticfiles
rm -rf gcpcul/staticfiles/summernote/

echo "--- 3. Cleaning media and temporary caches ---"
rm -rf gcpcul/media/
rm -rf og-generator/
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

echo "--- Build preparation complete ---"