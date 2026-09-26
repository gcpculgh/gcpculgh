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
    """Returns a configured Boto3 client targeting Cloudflare R2."""
    return boto3.client(
        's3',
        endpoint_url=settings.CLOUDFLARE_R2_ENDPOINT,
        aws_access_key_id=settings.CLOUDFLARE_ACCESS_KEY,
        aws_secret_access_key=settings.CLOUDFLARE_SECRET_KEY,
        region_name='auto',
    )


def _verify_and_promote_r2_file(r2_key):
    """
    Zero-Trust Quarantine Inspector:
    1. Reads the quarantined object from Cloudflare R2.
    2. Enforces strict byte-level hex validation (PDF, DOC, DOCX).
    3. Computes SHA-256 cryptographic checksum for immutable auditing.
    4. Extracts true document metadata (page count via pypdf).
    5. Moves the verified file from quarantine/ to documents/ and scrubs quarantine.
    """
    s3_client = _get_s3_client()
    bucket = settings.CLOUDFLARE_BUCKET_NAME

    # 1. Fetch file from quarantine
    response = s3_client.get_object(Bucket=bucket, Key=r2_key)
    file_bytes = response['Body'].read()

    # 2. Strict Magic Byte / Hex Inspection
    header = file_bytes[:8]
    is_pdf = header.startswith(b'%PDF')
    is_docx = header.startswith(b'PK\x03\x04')
    is_doc = header.startswith(b'\xd0\xcf\x11\xe0')

    if not (is_pdf or is_docx or is_doc):
        # Scrub quarantine immediately on spoofed upload
        s3_client.delete_object(Bucket=bucket, Key=r2_key)
        raise ValueError("Invalid file structure. Only genuine PDF, DOC, and DOCX files are permitted.")

    # 3. Cryptographic Immutability (SHA-256)
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # 4. Edge Metadata Extraction
    page_count = None
    if is_pdf:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            page_count = len(reader.pages)
        except Exception:
            page_count = None

    # 5. Promote from quarantine/ to documents/
    ext = r2_key.split('.')[-1].lower()
    clean_key = f"documents/{uuid.uuid4().hex}.{ext}"

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
                'Bucket': settings.CLOUDFLARE_BUCKET_NAME,
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
            'Bucket': settings.CLOUDFLARE_BUCKET_NAME,
            'Key': doc.document.name,
            'ResponseContentDisposition': f'attachment; filename="{doc.title}.pdf"'
        },
        ExpiresIn=900  # 15 minutes
    )
    return redirect(presigned_url)


@staff_required
def document_list(request):
    documents = Document.objects.all()

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
        "total_count": Document.objects.count(),
        "uploaded_count": Document.objects.exclude(document="").count(),
    }
    return render(request, "cms/admin_downloads.html", context)


@staff_required
def document_create(request):
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        r2_file_key = request.POST.get('r2_file_key', '').strip()

        # If direct-to-R2 was used, bypass standard form requirement for 'document'
        if r2_file_key and 'document' in form.errors:
            del form.errors['document']

        if form.is_valid():
            doc = form.save(commit=False)

            if r2_file_key:
                try:
                    verification = _verify_and_promote_r2_file(r2_file_key)
                    doc.document.name = verification['clean_key']

                    # Edge metadata population
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
            messages.error(request, "Upload failed. Please check the form for errors.")
    else:
        form = DocumentForm()
    return render(request, "cms/admin_downloads.html", {"form": form, "editing": None, "open_upload": True})


@staff_required
def document_update(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES, instance=document)
        r2_file_key = request.POST.get('r2_file_key', '').strip()

        if r2_file_key and 'document' in form.errors:
            del form.errors['document']

        if form.is_valid():
            doc = form.save(commit=False)

            if r2_file_key:
                try:
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
            messages.error(request, "Update failed. Please check the form for errors.")
    else:
        form = DocumentForm(instance=document)
    return render(request, "cms/admin_downloads.html", {"form": form, "editing": document, "open_upload": True})


@require_POST
@staff_required
def document_delete(request, pk):
    document = get_object_or_404(Document, pk=pk)
    title = document.title
    document.delete()
    messages.success(request, f'"{title}" deleted.')
    return redirect("cms:document_list")


# GALLERY

@staff_required
def gallery_list(request):
    albums = GalleryAlbum.objects.all()
    context = {
        "albums": albums,
        "album_count": albums.count(),
        "media_count": GalleryMedia.objects.count(),
        "stock_album_count": sum(1 for a in albums if a.uses_placeholder_media),
    }
    return render(request, "cms/admin_gallery.html", context)

def _save_gallery_media(request, album):
    """
    Shared by create/update. Expects, per new item i:
      media_files       -> request.FILES.getlist (the uploaded files themselves)
      captions           -> request.POST.getlist (parallel to media_files)
      media_types         -> request.POST.getlist ('image' | 'video', parallel to media_files)
    """
    files = request.FILES.getlist("media_files")
    captions = request.POST.getlist("captions")
    media_types = request.POST.getlist("media_types")

    new_items = []
    starting_order = album.media.count()
    for i, f in enumerate(files):
        caption = captions[i] if i < len(captions) else ""
        media_type = media_types[i] if i < len(media_types) else "image"
        
        # ZERO-TRUST COMPRESSION: Intercept image files and optimize them before saving
        if media_type == 'image':
            f = optimize_and_convert_to_webp(f, max_width=1600, quality=80)

        new_items.append(
            GalleryMedia(
                album=album, file=f, caption=caption,
                media_type=media_type, order=starting_order + i,
            )
        )
    GalleryMedia.objects.bulk_create(new_items)

def _update_existing_media(request):
    ids = request.POST.getlist("existing_media_id")
    captions = request.POST.getlist("existing_caption")
    types = request.POST.getlist("existing_media_type")
    for i, media_id in enumerate(ids):
        GalleryMedia.objects.filter(pk=media_id).update(
            caption=captions[i] if i < len(captions) else "",
            media_type=types[i] if i < len(types) else "image",
        )


def _apply_cover_selection(request, album):
    cover_key = request.POST.get("cover_key", "")  # e.g. "existing-14" or "new-2"
    if not cover_key:
        return
    album.media.update(is_cover=False)
    if cover_key.startswith("existing-"):
        media_id = cover_key.split("-", 1)[1]
        GalleryMedia.objects.filter(pk=media_id, album=album).update(is_cover=True)
    elif cover_key.startswith("new-"):
        new_index = int(cover_key.split("-", 1)[1])
        ordered_new = list(album.media.order_by("-id")[: len(request.FILES.getlist("media_files"))])
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
            _save_gallery_media(request, album)
            _apply_cover_selection(request, album)
            if not album.media.filter(is_cover=True).exists():
                first = album.media.first()
                if first:
                    first.is_cover = True
                    first.save()
            messages.success(request, f'"{album.title}" created with {album.media_count} item(s).')
            return redirect("cms:gallery_list")
    else:
        form = GalleryAlbumForm()
    return render(request, "cms/admin_gallery.html", {"form": form, "editing": None, "open_editor": True})


@staff_required
def gallery_update(request, pk):
    album = get_object_or_404(GalleryAlbum, pk=pk)
    if request.method == "POST":
        form = GalleryAlbumForm(request.POST, instance=album)
        if form.is_valid():
            album = form.save()
            _update_existing_media(request)
            _save_gallery_media(request, album)
            _apply_cover_selection(request, album)
            messages.success(request, f'"{album.title}" updated.')
            return redirect("cms:gallery_list")
    else:
        form = GalleryAlbumForm(instance=album)
    return render(
        request, "cms/admin_gallery.html",
        {"form": form, "editing": album, "existing_media": album.media.all(), "open_editor": True},
    )


@require_POST
@staff_required
def gallery_delete(request, pk):
    album = get_object_or_404(GalleryAlbum, pk=pk)
    title = album.title
    album.delete()  # CASCADE removes its GalleryMedia rows too
    messages.success(request, f'"{title}" and its media deleted.')
    return redirect("cms:gallery_list")


@require_POST
@staff_required
def gallery_media_delete(request, pk):
    """Removes a single already-saved photo/video from an album without
    resubmitting the whole album form — the 'x' button on an existing
    media tile in the editor calls this directly."""
    media = get_object_or_404(GalleryMedia, pk=pk)
    album_id = media.album_id
    media.file.delete(save=False)
    media.delete()
    return redirect("cms:gallery_update", pk=album_id)