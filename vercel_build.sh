#!/usr/bin/env bash
set -o errexit

echo "--- 1. Stripping AWS site-package bloat from Vercel's environment ---"
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

echo "--- 2. Compiling Django static assets ---"
cd gcpcul
python manage.py collectstatic --noinput
python manage.py compress --force
cd ..

echo "--- 3. Nuking media (and preserving Compressor manifest) ---"
# Save the CACHE folder before nuking staticfiles
if [ -d "gcpcul/staticfiles/CACHE" ]; then
    mv gcpcul/staticfiles/CACHE ./compressor_cache_backup
fi

rm -rf gcpcul/staticfiles/
mkdir -p gcpcul/staticfiles/

# Restore the CACHE folder so Vercel can find the manifest
if [ -d "./compressor_cache_backup" ]; then
    mv ./compressor_cache_backup gcpcul/staticfiles/CACHE
fi

rm -rf gcpcul/media/
rm -rf og-generator/

echo "--- 4. Cleaning temporary caches ---"
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

echo "--- Build preparation complete ---"