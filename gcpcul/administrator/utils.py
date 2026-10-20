import os
from io import BytesIO
from PIL import Image, ImageOps
from django.core.files.uploadedfile import InMemoryUploadedFile


def optimize_and_convert_to_webp(image_file, max_width=1600, max_height=1600, quality=82):
    if not image_file:
        return image_file

    try:
        img = Image.open(image_file)

        # 1. CRITICAL: Apply mobile camera EXIF orientation before stripping metadata
        img = ImageOps.exif_transpose(img)

        # 2. Preserve native WebP transparency (RGBA) instead of forcing a white box,
        #    while converting palette/CMYK images cleanly.
        if img.mode == 'P':
            img = img.convert('RGBA' if 'transparency' in img.info else 'RGB')
        elif img.mode == 'LA':
            img = img.convert('RGBA')
        elif img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')

        # 3. Bound BOTH width and height while preserving exact aspect ratio
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format='WEBP', quality=quality, method=6)

        file_size = buffer.tell()
        buffer.seek(0)

        base_name = os.path.basename(image_file.name).rsplit('.', 1)[0]
        new_filename = f"{base_name}.webp"

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