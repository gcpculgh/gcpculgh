"""
cms/views.py

Function-based views on purpose: the admin templates are hand-built with
very specific markup (custom table rows, the split-pane news editor, the
multi-file gallery dropzone) that doesn't map cleanly onto Django's generic
class-based views without fighting them. Straight views keep the POST
contracts explicit and easy to trace back to the template JS that submits
them.
"""
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
import boto3
from django.conf import settings

import io
import uuid
import base64
import hashlib
from pypdf import PdfReader
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.files.base import ContentFile

from .forms import DocumentForm
from .models import Document

from PIL import Image, ImageDraw, ImageFont, ImageOps

import json
from django.http import JsonResponse
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.shortcuts import get_object_or_404, redirect

from .forms import DocumentForm, GalleryAlbumForm, NewsArticleForm
from .models import Document, GalleryAlbum, GalleryMedia, NewsArticle
from .utils import optimize_and_convert_to_webp
from django.utils import timezone
from django.utils.text import slugify

from django.core.paginator import Paginator 

# Every view below is content-management, not member-facing — staff_member_required
# (checks request.user.is_staff) is deliberate here instead of login_required, which
# only checks "is someone logged in." Once the public Member Portal is live, an
# ordinary authenticated member must NOT be able to reach these views.

# Checks if user is logged in AND has staff privileges
staff_required = user_passes_test(lambda u: u.is_active and u.is_staff)

@staff_required
def dashboard(request):
    published_count = NewsArticle.objects.filter(status="published").count()
    draft_count = NewsArticle.objects.filter(status="draft").count()

    # 1. DOCUMENT VAULT LOGIC (Ignoring archived files)
    active_docs = Document.objects.filter(is_deleted=False)
    documents_total = active_docs.count()
    documents_uploaded = active_docs.exclude(document="").count()
    documents_pending = documents_total - documents_uploaded
    archived_docs_count = Document.objects.filter(is_deleted=True).count()

    # 2. GALLERY LOGIC (Separating Live, Drafts, and Archived)
    active_albums = GalleryAlbum.objects.filter(is_deleted=False)
    published_album_count = active_albums.filter(status='published').count()
    draft_album_count = active_albums.filter(status='draft').count()
    archived_album_count = GalleryAlbum.objects.filter(is_deleted=True).count()
    
    active_media_count = GalleryMedia.objects.filter(is_deleted=False).count()
    stock_album_count = sum(1 for a in active_albums if a.uses_placeholder_media)

    pending_agm_docs = Document.objects.filter(category="agm").filter(document="")

    # Items with a real query behind them.
    attention_items = []
    if pending_agm_docs.exists():
        years = ", ".join(str(d.year) for d in pending_agm_docs.order_by("year") if d.year)
        attention_items.append({
            "severity": "high", "icon": "description",
            "title": f"{pending_agm_docs.count()} AGM document(s) awaiting upload",
            "body": f"{years} AGM minutes & reports haven't been added to the Vault yet." if years else "Some AGM documents are missing their file.",
            "url_name": "cms:document_list",
        })
    if stock_album_count > 0:
        attention_items.append({
            "severity": "high", "icon": "image",
            "title": f"{stock_album_count} gallery album(s) still on stock photography",
            "body": "Real event photos are needed before these go live publicly.",
            "url_name": "cms:gallery_list",
        })
    if draft_count > 0:
        attention_items.append({
            "severity": "med", "icon": "edit_note",
            "title": f"{draft_count} article(s) saved as drafts",
            "body": "Review and publish, or continue editing.",
            "url_name": "cms:news_list",
        })

    recent_activity = []

    for article in NewsArticle.objects.order_by("-updated_at")[:3]:
        recent_activity.append({
            "type": "article", "title": article.title,
            "author": getattr(article, "author", "Admin"),
            "status": article.status, "timestamp": article.updated_at, "icon": "edit_square"
        })

    for doc in Document.objects.exclude(document="").order_by("-created_at")[:3]:
        recent_activity.append({
            "type": "document", "title": doc.title,
            "author": "Admin", "timestamp": doc.created_at, "icon": "upload_file"
        })

    # Bring Gallery Albums into the timeline
    for album in GalleryAlbum.objects.filter(is_deleted=False).order_by("-id")[:3]:
        ts = getattr(album, 'updated_at', getattr(album, 'created_at', timezone.now()))
        recent_activity.append({
            "type": "album", "title": album.title,
            "author": "Admin", "timestamp": ts, "icon": "photo_library"
        })

    # Sort the combined list chronologically (newest first)
    recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)

    context = {
        "published_count": published_count,
        "draft_count": draft_count,
        
        "documents_uploaded": documents_uploaded,
        "documents_pending": documents_pending,
        "archived_docs_count": archived_docs_count, 
        
        "published_album_count": published_album_count, 
        "draft_album_count": draft_album_count,         
        "archived_album_count": archived_album_count,   
        "active_media_count": active_media_count,       
        
        "attention_items": attention_items,
        "attention_count": len(attention_items),
        "recent_activity": recent_activity[:5], 
    }
    return render(request, "cms/admin_dashboard.html", context)


# NEWS & BLOG

@staff_required
def news_list(request):
    articles = NewsArticle.objects.all()

    query = request.GET.get("q", "").strip()
    if query:
        articles = articles.filter(title__icontains=query)

    status = request.GET.get("status", "all")
    if status in ("draft", "published"):
        articles = articles.filter(status=status)

    context = {
        "articles": articles,
        "query": query,
        "status": status,
        "published_count": NewsArticle.objects.filter(status="published").count(),
        "draft_count": NewsArticle.objects.filter(status="draft").count(),
    }
    return render(request, "cms/admin_news.html", context)


@staff_required
def news_create(request):
    if request.method == "POST":
        form = NewsArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save()
            messages.success(request, f'"{article.title}" saved as {article.get_status_display().lower()}.')
            return redirect("cms:news_list")
    else:
        form = NewsArticleForm(initial={"status": "draft"})
    return render(request, "cms/admin_news.html", {"form": form, "editing": None, "open_editor": True})


@staff_required
def news_update(request, public_id):
    article = get_object_or_404(NewsArticle, public_id=public_id)
    if request.method == "POST":
        form = NewsArticleForm(request.POST, request.FILES, instance=article)
        if form.is_valid():
            article = form.save()
            messages.success(request, f'"{article.title}" updated.')
            return redirect("cms:news_list")
    else:
        form = NewsArticleForm(instance=article)
    return render(request, "cms/admin_news.html", {"form": form, "editing": article, "open_editor": True})


@require_POST
@staff_required
def news_delete(request, public_id):
    article = get_object_or_404(NewsArticle, public_id=public_id)
    title = article.title
    article.delete()
    messages.success(request, f'"{title}" deleted.')
    return redirect("cms:news_list")


# ============================================================
# DOCUMENT VAULT
# ============================================================
def _get_s3_client():
    """Returns a configured Boto3 client targeting Cloudflare R2 using your existing AWS settings."""
    return boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME or 'auto',
    )

def _verify_and_promote_r2_file(r2_key, file_category="document", wm_config=None):
    s3_client = _get_s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME

    response = s3_client.get_object(Bucket=bucket, Key=r2_key)
    file_bytes = response['Body'].read()

    clean_bytes = file_bytes.lstrip()
    header = clean_bytes[:12]
    
    is_valid = False
    page_count = None

    if file_category == "document":
        is_pdf = header.startswith(b'%PDF')
        is_docx = file_bytes.startswith(b'PK\x03\x04')
        is_doc = file_bytes.startswith(b'\xd0\xcf\x11\xe0')
        is_valid = is_pdf or is_docx or is_doc
        if is_pdf:
            try:
                reader = PdfReader(io.BytesIO(file_bytes))
                page_count = len(reader.pages)
            except Exception:
                page_count = None
                
    elif file_category == "media":
        is_webp = header.startswith(b'RIFF') and clean_bytes[8:12] == b'WEBP'
        is_jpeg = header.startswith(b'\xff\xd8\xff')
        is_png = header.startswith(b'\x89PNG')
        is_mp4 = clean_bytes[4:8] == b'ftyp'
        is_valid = is_webp or is_jpeg or is_png or is_mp4

    if not is_valid:
        s3_client.delete_object(Bucket=bucket, Key=r2_key)
        raise ValueError(f"Spoofed or invalid {file_category} detected.")

    # APPLY SERVER-SIDE WATERMARK IF MEDIA
    if file_category == "media" and wm_config and wm_config.get('enabled'):
        file_bytes = _apply_server_side_watermark(file_bytes, wm_config, s3_client, bucket)

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    ext = 'webp' if file_category == "media" else r2_key.split('.')[-1].lower()
    folder = "gallery" if file_category == "media" else "documents"
    clean_key = f"{folder}/{uuid.uuid4().hex}.{ext}"

    s3_client.put_object(
        Bucket=bucket,
        Key=clean_key,
        Body=file_bytes,
        ContentType='image/webp' if file_category == "media" else 'application/octet-stream'
    )
    s3_client.delete_object(Bucket=bucket, Key=r2_key)

    return {
        'clean_key': clean_key,
        'sha256_hash': sha256_hash,
        'page_count': page_count,
        'file_size': len(file_bytes), # The new file size calculation
    }

@require_POST
@staff_required
def gallery_auto_save(request):
    """
    Enterprise Shadow Save:
    Silently pinged by the browser to lock Cloudflare uploads and text changes 
    into the database as a draft, preventing data loss if the device dies.
    """
    try:
        data = json.loads(request.body)
        album_id = data.get('album_id')
        if album_id:
            album = get_object_or_404(GalleryAlbum, public_id=album_id, is_deleted=False)
        else:
            album = GalleryAlbum.objects.create(status='draft')

        # 1. Sync Metadata
        album.title = data.get('title', album.title)
        album.subtitle = data.get('subtitle', album.subtitle)
        album.category = data.get('category', album.category)
        
        if data.get('publish'):
            album.status = 'published'
            
        album.save()

        # 2. Process newly streamed Cloudflare files from the quarantine bucket
        new_media_payload = data.get('new_media', [])
        starting_order = album.media.filter(is_deleted=False).count()
        watermark_config = data.get('watermark_config', {})
        
        saved_media = []

        # SERVERLESS OPTIMIZATION: Sequential processing avoids thread starvation and deadlocks on Vercel.
        for i, media_item in enumerate(new_media_payload):
            r2_key = media_item.get('r2_key')
            if not r2_key:
                continue
            
            try:
                # Verify, watermark (via Pillow), and promote sequentially
                verification = _verify_and_promote_r2_file(r2_key, file_category="media", wm_config=watermark_config)
                
                new_obj = GalleryMedia.objects.create(
                    album=album,
                    file=verification['clean_key'],
                    caption=media_item.get('caption', ''),
                    media_type=media_item.get('type', 'image'),
                    order=starting_order + i,
                    file_hash=verification['sha256_hash']
                )
                
                saved_media.append({
                    'frontend_id': media_item.get('frontend_id'), 
                    'db_id': str(new_obj.public_id),
                    'clean_url': new_obj.file.url
                })
            except Exception as e:
                # ENTERPRISE RESILIENCE: If a file is missing in Cloudflare or invalid, 
                # skip it gracefully instead of throwing a 400 and crashing the whole batch.
                print(f"Skipping missing or invalid media {r2_key}: {e}")
                continue

        # 3. Handle batch text updates for existing photos
        existing_updates = data.get('existing_media_updates', [])
        for u in existing_updates:
            GalleryMedia.objects.filter(public_id=u['db_id'], album=album).update(
                caption=u.get('caption', ''),
                media_type=u.get('type', 'image')
            )
            
        # 4. THE ENTERPRISE FIX: Micro-Batch Safe Garbage Collection
        if 'active_db_ids' in data:
            frontend_active_ids = data.get('active_db_ids', [])
            newly_saved_uuids = [item['db_id'] for item in saved_media]
            all_keep_uuids = frontend_active_ids + newly_saved_uuids
            
            album.media.filter(is_deleted=False).exclude(public_id__in=all_keep_uuids).update(
                is_deleted=True,
                deleted_at=timezone.now()
            )
            
        # 5. Lock in the cover photo
        cover_id = data.get('cover_db_id')
        if cover_id:
            album.media.filter(is_deleted=False).update(is_cover=False)
            album.media.filter(public_id=cover_id, is_deleted=False).update(is_cover=True)

        return JsonResponse({
            'success': True,
            'album_id': str(album.public_id), 
            'saved_media': saved_media
        })
        
    except ValueError as ve:
        return JsonResponse({'success': False, 'error': f"Security Alert: {str(ve)}"}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    
def _apply_server_side_watermark(file_bytes, wm_config, s3_client=None, bucket_name=None):
    """
    Enterprise Server-Side Watermarking Engine using Pillow.
    Applies text or image watermarks with dynamic scaling, opacity, and border-radius clipping.
    """
    if not wm_config or not wm_config.get('enabled'):
        return file_bytes

    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
        
        # ENTERPRISE FIX 1: Normalize hidden EXIF rotation from mobile cameras
        img = ImageOps.exif_transpose(img)
        width, height = img.size

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        opacity = float(wm_config.get('opacity', 80)) / 100.0
        scale = float(wm_config.get('size', 15)) / 100.0
        position = wm_config.get('position', 'bottom-right')
        
        # ENTERPRISE FIX 2: Base scaling and padding on the longest edge to normalize portrait/landscape sizing
        base_dim = max(width, height)
        pad = int(base_dim * 0.02)

        wm_type = wm_config.get('type', 'text')

        if wm_type == 'text':
            text = wm_config.get('text', 'GCPCUL').strip()
            if text:
                font_size = int(base_dim * scale)
                
                font_path = os.path.join(settings.BASE_DIR, 'cms', 'fonts', 'arial.ttf')
                try:
                    font = ImageFont.truetype(font_path, font_size)
                except IOError:
                    font = ImageFont.load_default()

                bbox = draw.textbbox((0, 0), text, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]

                if 'right' in position:
                    x = width - text_w - pad
                elif 'left' in position:
                    x = pad
                else:
                    x = (width - text_w) // 2

                if 'bottom' in position:
                    y = height - text_h - pad
                elif 'top' in position:
                    y = pad
                else:
                    y = (height - text_h) // 2

                color_hex = wm_config.get('color', '#ffffff').lstrip('#')
                rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
                color_rgba = rgb + (int(255 * opacity),)

                shadow_rgba = (0, 0, 0, int(255 * opacity * 0.6))
                draw.text((x + 2, y + 2), text, font=font, fill=shadow_rgba)
                draw.text((x, y), text, font=font, fill=color_rgba)

        elif wm_type == 'image':
            logo_base64 = wm_config.get('logo_base64')
            if logo_base64:
                try:
                    if ',' in logo_base64:
                        _, logo_base64 = logo_base64.split(',', 1)
                    
                    logo_bytes = base64.b64decode(logo_base64)
                    logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")

                    # Mathematical sizing based on the longest edge of the main photo
                    logo_w = int(base_dim * scale)
                    logo_h = int(logo_img.height * (logo_w / logo_img.width))
                    logo_img = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)

                    wm_radius = float(wm_config.get('radius', 0)) / 100.0
                    if wm_radius > 0:
                        radius_px = int(min(logo_w, logo_h) * wm_radius)
                        mask = Image.new("L", (logo_w, logo_h), 0)
                        draw_mask = ImageDraw.Draw(mask)
                        draw_mask.rounded_rectangle((0, 0, logo_w, logo_h), radius=radius_px, fill=255)
                        logo_img.putalpha(mask)

                    if opacity < 1.0:
                        r, g, b, alpha = logo_img.split()
                        alpha = alpha.point(lambda p: int(p * opacity))
                        logo_img.putalpha(alpha)

                    if 'right' in position:
                        x = width - logo_w - pad
                    elif 'left' in position:
                        x = pad
                    else:
                        x = (width - logo_w) // 2

                    if 'bottom' in position:
                        y = height - logo_h - pad
                    elif 'top' in position:
                        y = pad
                    else:
                        y = (height - logo_h) // 2

                    overlay.paste(logo_img, (x, y), logo_img)
                except Exception as logo_err:
                    print(f"Server-side logo watermark error: {logo_err}")

        watermarked = Image.alpha_composite(img, overlay)
        out_io = io.BytesIO()
        watermarked.convert("RGB").save(out_io, format="WEBP", quality=85)
        return out_io.getvalue()
    except Exception as e:
        print(f"Watermark processing error: {e}")
        return file_bytes
 
@staff_required
def generate_upload_url(request):
    """Generates a secure, temporary direct-to-Cloudflare R2 upload URL."""
    filename = request.GET.get('filename', 'document.pdf')
    content_type = request.GET.get('content_type', 'application/pdf')

    ext = filename.split('.')[-1].lower()
    unique_key = f"quarantine/{uuid.uuid4().hex}.{ext}"
    s3_client = _get_s3_client()

    try:
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': unique_key,
                'ContentType': content_type,
            },
            ExpiresIn=3600
        )
        return JsonResponse({
            'upload_url': presigned_url,
            'file_key': unique_key
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def secure_document_download(request, public_id):
    """
    Public JIT Download Gateway.
    No login required for members, but keeps R2 fully private.
    Issues a short-lived (15-minute) signed link to prevent permanent hotlinking.
    """
    doc = get_object_or_404(Document, public_id=public_id)
    
    if not doc.document:
        messages.error(request, "This document file is not yet available.")
        return redirect("cms:document_list")

    s3_client = _get_s3_client()
    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': doc.document.name,
            'ResponseContentDisposition': f'attachment; filename="{doc.title}.pdf"'
        },
        ExpiresIn=900  # 15 minutes
    )
    return redirect(presigned_url)



def secure_media_download(request, public_id):
    """
    Public JIT Media Download Gateway.
    Forces Cloudflare to serve the file as a downloadable attachment 
    instead of rendering it inline in a new browser tab.
    """
    media = get_object_or_404(GalleryMedia, public_id=public_id, is_deleted=False)
    
    if not media.file:
        messages.error(request, "This media file is currently unavailable.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    s3_client = _get_s3_client()
    
    # Generate a clean, professional filename for the user's hard drive
    ext = media.file.name.split('.')[-1].lower() if '.' in media.file.name else 'webp'
    album_slug = slugify(media.album.title) if media.album.title else "gcpcul_gallery"
    clean_filename = f"{album_slug}_{str(media.public_id)[:8]}.{ext}"

    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': media.file.name,
            'ResponseContentDisposition': f'attachment; filename="{clean_filename}"'
        },
        ExpiresIn=60  # 60 seconds is plenty since it redirects instantly
    )
    return redirect(presigned_url)



@staff_required
def document_list(request):
    documents = Document.objects.filter(is_deleted=False)

    query = request.GET.get("q", "").strip()
    if query:
        documents = documents.filter(title__icontains=query)

    category = request.GET.get("category", "all")
    if category in dict(Document.CATEGORY_CHOICES):
        documents = documents.filter(category=category)

    # ADD PAGINATION (15 documents per page)
    paginator = Paginator(documents, 15) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "documents": page_obj, # Pass the paginated object instead of the full queryset
        "query": query,
        "category": category,
        "total_count": Document.objects.filter(is_deleted=False).count(),
        "uploaded_count": Document.objects.filter(is_deleted=False).exclude(document="").count(),
    }
    return render(request, "cms/admin_downloads.html", context)

@staff_required
def document_create(request):
    if request.method == "POST":
        # Pure decoupled form handling — no dummy files needed
        form = DocumentForm(request.POST)
        r2_file_key = request.POST.get('r2_file_key', '').strip()

        if form.is_valid():
            doc = form.save(commit=False)

            if r2_file_key:
                try:
                    # The true zero-trust validation happens securely in the cloud
                    verification = _verify_and_promote_r2_file(r2_file_key)
                    doc.document.name = verification['clean_key']

                    if verification['page_count'] is not None and hasattr(doc, 'pages'):
                        doc.pages = verification['page_count']

                    if hasattr(doc, 'file_hash'):
                        doc.file_hash = verification['sha256_hash']
                        
                    if hasattr(doc, 'file_size'):
                        doc.file_size = verification['file_size']

                except ValueError as ve:
                    messages.error(request, f"Security Alert: {str(ve)}")
                    return render(request, "cms/admin_downloads.html", {"form": form, "editing": None, "open_upload": True})
                except Exception as e:
                    messages.error(request, f"Cloudflare R2 verification error: {str(e)}")
                    return render(request, "cms/admin_downloads.html", {"form": form, "editing": None, "open_upload": True})

            # Save base64 canvas thumbnail if generated
            thumbnail_b64 = request.POST.get('thumbnail_base64', '')
            if thumbnail_b64 and hasattr(doc, 'thumbnail'):
                try:
                    if ';base64,' in thumbnail_b64:
                        fmt, imgstr = thumbnail_b64.split(';base64,', 1)
                        ext = fmt.split('/')[-1] if '/' in fmt else 'webp'
                        doc.thumbnail.save(
                            f"{uuid.uuid4().hex[:12]}.{ext}",
                            ContentFile(base64.b64decode(imgstr)),
                            save=False
                        )
                except Exception:
                    pass

            doc.save()
            messages.success(request, f'"{doc.title}" saved successfully.')
            return redirect("cms:document_list")
        else:
            for field, errors in form.errors.items():
                messages.error(request, f"{field.replace('_', ' ').title()}: {errors[0]}")
    else:
        form = DocumentForm()
    return render(request, "cms/admin_downloads.html", {"form": form, "editing": None, "open_upload": True})


@staff_required
def document_update(request, public_id):
    document = get_object_or_404(Document, public_id=public_id)
    if request.method == "POST":
        # Pure decoupled form handling — no dummy files needed
        form = DocumentForm(request.POST, instance=document)
        r2_file_key = request.POST.get('r2_file_key', '').strip()

        if form.is_valid():
            doc = form.save(commit=False)

            if r2_file_key:
                try:
                    # The true zero-trust validation happens securely in the cloud
                    verification = _verify_and_promote_r2_file(r2_file_key)
                    doc.document.name = verification['clean_key']

                    if verification['page_count'] is not None and hasattr(doc, 'pages'):
                        doc.pages = verification['page_count']

                    if hasattr(doc, 'file_hash'):
                        doc.file_hash = verification['sha256_hash']
                        
                    if hasattr(doc, 'file_size'):
                        doc.file_size = verification['file_size']

                except ValueError as ve:
                    messages.error(request, f"Security Alert: {str(ve)}")
                    return render(request, "cms/admin_downloads.html", {"form": form, "editing": document, "open_upload": True})
                except Exception as e:
                    messages.error(request, f"Cloudflare R2 verification error: {str(e)}")
                    return render(request, "cms/admin_downloads.html", {"form": form, "editing": document, "open_upload": True})

            # Save base64 canvas thumbnail if generated
            thumbnail_b64 = request.POST.get('thumbnail_base64', '')
            if thumbnail_b64 and hasattr(doc, 'thumbnail'):
                try:
                    if ';base64,' in thumbnail_b64:
                        fmt, imgstr = thumbnail_b64.split(';base64,', 1)
                        ext = fmt.split('/')[-1] if '/' in fmt else 'webp'
                        doc.thumbnail.save(
                            f"{uuid.uuid4().hex[:12]}.{ext}",
                            ContentFile(base64.b64decode(imgstr)),
                            save=False
                        )
                except Exception:
                    pass

            doc.save()
            messages.success(request, f'"{doc.title}" updated successfully.')
            return redirect("cms:document_list")
        else:
            for field, errors in form.errors.items():
                messages.error(request, f"{field.replace('_', ' ').title()}: {errors[0]}")
    else:
        form = DocumentForm(instance=document)
    return render(request, "cms/admin_downloads.html", {"form": form, "editing": document, "open_upload": True})

@require_POST
@staff_required
def document_delete(request, public_id):
    document = get_object_or_404(Document, public_id=public_id)
    
    # ENTERPRISE STANDARD: Soft Delete
    document.is_deleted = True
    document.deleted_at = timezone.now()
    document.save()
    
    messages.success(request, f'"{document.title}" has been archived and removed from the vault.')
    return redirect("cms:document_list")


@staff_required
def gallery_list(request):
    # Only fetch albums that haven't been soft-deleted
    albums = GalleryAlbum.objects.filter(is_deleted=False)
    context = {
        "albums": albums,
        "album_count": albums.count(),
        "media_count": GalleryMedia.objects.filter(is_deleted=False).count(),
        "stock_album_count": sum(1 for a in albums if a.uses_placeholder_media),
    }
    return render(request, "cms/admin_gallery.html", context)

def _process_parallel_media(request, album):
    """
    Enterprise Parallel Upload Handler:
    Intercepts the array of R2 keys sent by the frontend, verifies them 
    in the cloud, and writes the database records atomically.
    """
    r2_keys = request.POST.getlist("r2_media_keys")
    captions = request.POST.getlist("captions")
    media_types = request.POST.getlist("media_types")

    new_items = []
    starting_order = album.media.filter(is_deleted=False).count()
    
    for i, r2_key in enumerate(r2_keys):
        if not r2_key.strip():
            continue
            
        caption = captions[i] if i < len(captions) else ""
        media_type = media_types[i] if i < len(media_types) else "image"
        
        try:
            # Verify and pull from the quarantine bucket
            verification = _verify_and_promote_r2_file(r2_key, file_category="media")
            
            new_items.append(
                GalleryMedia(
                    album=album, 
                    file=verification['clean_key'], 
                    caption=caption,
                    media_type=media_type, 
                    order=starting_order + i,
                    file_hash=verification['sha256_hash']
                )
            )
        except Exception as e:
            # Log the failure but don't crash the entire batch upload
            print(f"Skipping failed media item: {e}")
            
    if new_items:
        GalleryMedia.objects.bulk_create(new_items)


def _update_existing_media(request):
    ids = request.POST.getlist("existing_media_id")
    captions = request.POST.getlist("existing_caption")
    types = request.POST.getlist("existing_media_type")
    for i, media_id in enumerate(ids):
        GalleryMedia.objects.filter(public_id=media_id, is_deleted=False).update(
            caption=captions[i] if i < len(captions) else "",
            media_type=types[i] if i < len(types) else "image",
        )

def _apply_cover_selection(request, album):
    cover_key = request.POST.get("cover_key", "")
    if not cover_key:
        return
    
    album.media.filter(is_deleted=False).update(is_cover=False)
    
    if cover_key.startswith("existing-"):
        media_id = cover_key.split("-", 1)[1]
        GalleryMedia.objects.filter(public_id=media_id, album=album, is_deleted=False).update(is_cover=True)
    elif cover_key.startswith("new-"):
        new_index = int(cover_key.split("-", 1)[1])
        ordered_new = list(album.media.filter(is_deleted=False).order_by("-id")[: len(request.POST.getlist("r2_media_keys"))])
        ordered_new.reverse()
        if 0 <= new_index < len(ordered_new):
            ordered_new[new_index].is_cover = True
            ordered_new[new_index].save()

@staff_required
def gallery_create(request):
    if request.method == "POST":
        form = GalleryAlbumForm(request.POST)
        if form.is_valid():
            album = form.save()
            _process_parallel_media(request, album)
            _apply_cover_selection(request, album)
            
            # Ensure at least one cover exists
            if not album.media.filter(is_cover=True, is_deleted=False).exists():
                first = album.media.filter(is_deleted=False).first()
                if first:
                    first.is_cover = True
                    first.save()
                    
            messages.success(request, f'"{album.title}" created with {album.media_count} item(s).')
            return redirect("cms:gallery_list")
        else:
            for field, errors in form.errors.items():
                messages.error(request, f"{field.replace('_', ' ').title()}: {errors[0]}")
    else:
        form = GalleryAlbumForm()
    return render(request, "cms/admin_gallery.html", {"form": form, "editing": None, "open_editor": True})


@staff_required
def gallery_update(request, public_id):
    album = get_object_or_404(GalleryAlbum, public_id=public_id, is_deleted=False)
    if request.method == "POST":
        form = GalleryAlbumForm(request.POST, instance=album)
        if form.is_valid():
            album = form.save()
            _update_existing_media(request)
            _process_parallel_media(request, album)
            _apply_cover_selection(request, album)
            messages.success(request, f'"{album.title}" updated.')
            return redirect("cms:gallery_list")
        else:
            for field, errors in form.errors.items():
                messages.error(request, f"{field.replace('_', ' ').title()}: {errors[0]}")
    else:
        form = GalleryAlbumForm(instance=album)
        
    return render(
        request, "cms/admin_gallery.html",
        {"form": form, "editing": album, "existing_media": album.media.filter(is_deleted=False), "open_editor": True},
    )


@require_POST
@staff_required
def gallery_delete(request, public_id):
    album = get_object_or_404(GalleryAlbum, public_id=public_id)
    title = album.title
    
    # Calls the custom method we added to models.py to soft-delete the album and all its media
    album.soft_delete()
    
    messages.success(request, f'"{title}" and its media have been archived.')
    return redirect("cms:gallery_list")


@require_POST
@staff_required
def gallery_media_delete(request, public_id): 
    media = get_object_or_404(GalleryMedia, public_id=public_id)
    album_public_id = media.album.public_id
    
    media.is_deleted = True
    media.deleted_at = timezone.now()
    media.save()
    
    return redirect("cms:gallery_update", public_id=album_public_id)


def custom_csrf_failure(request, reason=""):
    """Catches dead sessions and routes them gracefully instead of crashing."""
    from django.contrib import messages
    from django.shortcuts import redirect
    
    messages.error(request, "Your secure session expired due to inactivity. Please try saving again.")
    return redirect("administrator:dashboard")