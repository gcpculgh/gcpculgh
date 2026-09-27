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


from django.shortcuts import get_object_or_404, redirect

from .forms import DocumentForm, GalleryAlbumForm, NewsArticleForm
from .models import Document, GalleryAlbum, GalleryMedia, NewsArticle
from .utils import optimize_and_convert_to_webp
from django.utils import timezone

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

    documents_total = Document.objects.count()
    documents_uploaded = Document.objects.exclude(document="").count()
    documents_pending = documents_total - documents_uploaded

    albums = GalleryAlbum.objects.all()
    album_count = albums.count()
    media_count = GalleryMedia.objects.count()
    stock_album_count = sum(1 for a in albums if a.uses_placeholder_media)

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

    # Editorial items with no backing model yet — honestly labeled as
    # checklist entries rather than dressed up as live query results.
    attention_items += [
        {"severity": "med", "icon": "groups", "title": "Board & Committee photos are placeholders",
         "body": "Committee member management isn't built yet — tracked here as a reminder.", "url_name": None},
        {"severity": "med", "icon": "link_off", "title": "6 social media links are inactive",
         "body": "Footer links still point to placeholder URLs.", "url_name": None},
        {"severity": "med", "icon": "flag", "title": "Mission, Vision & Core Values need sign-off",
         "body": "Current wording needs official Board approval.", "url_name": None},
    ]

    context = {
        "published_count": published_count,
        "draft_count": draft_count,
        "documents_total": documents_total,
        "documents_uploaded": documents_uploaded,
        "documents_pending": documents_pending,
        "album_count": album_count,
        "media_count": media_count,
        "attention_items": attention_items,
        "attention_count": len(attention_items),
        "recent_articles": NewsArticle.objects.order_by("-updated_at")[:3],
        "recent_documents": Document.objects.exclude(document="").order_by("-created_at")[:2],
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
def news_update(request, pk):
    article = get_object_or_404(NewsArticle, pk=pk)
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
def news_delete(request, pk):
    article = get_object_or_404(NewsArticle, pk=pk)
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

def _verify_and_promote_r2_file(r2_key, file_category="document"):
    """
    Zero-Trust Quarantine Inspector: 
    Validates Magic Bytes, Hashes Payload, and Promotes File.
    """
    s3_client = _get_s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME

    response = s3_client.get_object(Bucket=bucket, Key=r2_key)
    file_bytes = response['Body'].read()

    clean_bytes = file_bytes.lstrip()
    header = clean_bytes[:12] # Expanded to 12 bytes to catch MP4/WebP signatures
    
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
        # Image formats (WebP is the target from our edge interceptor, plus fallbacks)
        is_webp = header.startswith(b'RIFF') and clean_bytes[8:12] == b'WEBP'
        is_jpeg = header.startswith(b'\xff\xd8\xff')
        is_png = header.startswith(b'\x89PNG')
        # Video format (MP4 ftyp box)
        is_mp4 = clean_bytes[4:8] == b'ftyp'
        
        is_valid = is_webp or is_jpeg or is_png or is_mp4

    if not is_valid:
        s3_client.delete_object(Bucket=bucket, Key=r2_key)
        raise ValueError(f"Spoofed or invalid {file_category} detected. Header: {header!r}")

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    ext = r2_key.split('.')[-1].lower()
    folder = "gallery" if file_category == "media" else "documents"
    clean_key = f"{folder}/{uuid.uuid4().hex}.{ext}"

    s3_client.copy_object(
        Bucket=bucket,
        CopySource={'Bucket': bucket, 'Key': r2_key},
        Key=clean_key,
    )
    s3_client.delete_object(Bucket=bucket, Key=r2_key)

    return {
        'clean_key': clean_key,
        'sha256_hash': sha256_hash,
        'page_count': page_count,
    }

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


def secure_document_download(request, doc_id):
    """
    Public JIT Download Gateway.
    No login required for members, but keeps R2 fully private.
    Issues a short-lived (15-minute) signed link to prevent permanent hotlinking.
    """
    doc = get_object_or_404(Document, id=doc_id)
    
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

@staff_required
def document_list(request):
    # Only fetch active documents
    documents = Document.objects.filter(is_deleted=False)

    query = request.GET.get("q", "").strip()
    if query:
        documents = documents.filter(title__icontains=query)

    category = request.GET.get("category", "all")
    if category in dict(Document.CATEGORY_CHOICES):
        documents = documents.filter(category=category)

    context = {
        "documents": documents,
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
def document_update(request, pk):
    document = get_object_or_404(Document, pk=pk)
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
def document_delete(request, pk):
    document = get_object_or_404(Document, pk=pk)
    
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
        GalleryMedia.objects.filter(pk=media_id, is_deleted=False).update(
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
        GalleryMedia.objects.filter(pk=media_id, album=album, is_deleted=False).update(is_cover=True)
    elif cover_key.startswith("new-"):
        new_index = int(cover_key.split("-", 1)[1])
        # Find the newly created items by ordering descending
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
def gallery_update(request, pk):
    album = get_object_or_404(GalleryAlbum, pk=pk, is_deleted=False)
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
def gallery_delete(request, pk):
    album = get_object_or_404(GalleryAlbum, pk=pk)
    title = album.title
    
    # Calls the custom method we added to models.py to soft-delete the album and all its media
    album.soft_delete()
    
    messages.success(request, f'"{title}" and its media have been archived.')
    return redirect("cms:gallery_list")


@require_POST
@staff_required
def gallery_media_delete(request, pk):
    media = get_object_or_404(GalleryMedia, pk=pk)
    album_id = media.album_id
    
    # Enterprise Soft Delete for a single item
    media.is_deleted = True
    media.deleted_at = timezone.now()
    media.save()
    
    return redirect("cms:gallery_update", pk=album_id)


def custom_csrf_failure(request, reason=""):
    """Catches dead sessions and routes them gracefully instead of crashing."""
    from django.contrib import messages
    from django.shortcuts import redirect
    
    messages.error(request, "Your secure session expired due to inactivity. Please try saving again.")
    return redirect("cms:dashboard")