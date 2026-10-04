#!/bin/bash

# 1. Compile Django static assets
cd gcpcul
python manage.py collectstatic --noinput
python manage.py compress --force
cd ..

echo "Running zero-trust bloat elimination..."

# 2. Physically nuke the 80MB AWS Botocore bloat
python -c "import botocore, os, shutil; d=os.path.join(os.path.dirname(botocore.__file__), 'data'); [shutil.rmtree(os.path.join(d, x), ignore_errors=True) for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)) and x not in ['s3', 's3control', 'sts', 'iam']]"

# 3. Destroy local databases, uploaded media, and heavy frontend folders
rm -rf gcpcul/db.sqlite3
rm -rf gcpcul/media/
rm -rf og-generator/

# 4. Wipe all compiled Python cache files (Saves ~10-15MB)
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

echo "Elimination complete. Ready for Vercel."