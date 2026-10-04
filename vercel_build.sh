#!/bin/bash

# 1. Enter the Django app directory
cd gcpcul

# 2. Compile and compress static assets
python manage.py collectstatic --noinput
python manage.py compress --force

# 3. Surgically prune AWS Botocore bloat to beat the 225MB limit
python -c "import botocore, os, shutil; d=os.path.join(os.path.dirname(botocore.__file__), 'data'); [shutil.rmtree(os.path.join(d, x), ignore_errors=True) for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)) and x not in ['s3', 's3control', 'sts', 'iam']]"

echo "Build and optimization complete."