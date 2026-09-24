import sys
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile

def optimize_and_convert_to_webp(image_file, max_width=1600, quality=80):
    if not image_file:
        return image_file

    try:
        img = Image.open(image_file)
        
        # 1. FIX: Properly composite transparent images onto a white background
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            img = img.convert('RGBA')
            background = Image.new('RGBA', img.size, (255, 255, 255))
            background.paste(img, (0, 0), img)
            img = background.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        if img.width > max_width:
            output_height = int((max_width / img.width) * img.height)
            img = img.resize((max_width, output_height), Image.Resampling.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format='WEBP', quality=quality, method=6)
        
        # 2. FIX: Get the actual byte payload size of the image, not the Python object
        file_size = buffer.tell()
        buffer.seek(0)

        original_name = image_file.name.rsplit('.', 1)[0]
        new_filename = f"{original_name}.webp"

        return InMemoryUploadedFile(
            buffer,
            'ImageField',
            new_filename,
            'image/webp',
            file_size,
            None
        )
    except Exception as e:
        print(f"Image optimization pipeline failed: {e}")
        return image_file