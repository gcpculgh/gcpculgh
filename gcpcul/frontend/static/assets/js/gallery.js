function showToast(message, type = 'success') {
    const toast = document.getElementById('toastNotification');
    const iconSvg = type === 'success'
        ? '<span class="material-symbols-outlined">check_circle</span>'
        : '<span class="material-symbols-outlined">warning</span>';

    toast.className = `toast-notification toast-${type} show`;
    toast.innerHTML = `<span class="icon-svg toast-icon">${iconSvg}</span><span>${message}</span>`;

    setTimeout(() => { toast.classList.remove('show'); }, 3500);
}

/* DYNAMIC DJANGO ALBUMS DATABASE (Zero-Trust R2 Links) */
const ALBUMS_DATA = {
    {% for album in albums %}
"{{ album.public_id }}": { /* ENTERPRISE FIX: Secure UUID Key */
    title: "{{ album.title|escapejs }}",
        subtitle: "{{ album.subtitle|escapejs }}",
            photos: [
                {% for media in album.media.all %}
{% if not media.is_deleted and media.file %}
{
    type: "{{ media.media_type }}",
        src: "{{ media.file.url|escapejs }}",
            thumb: "{% if media.media_type == 'video' %}data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII={% else %}{{ media.file.url|escapejs }}{% endif %}",
                caption: "{{ media.caption|default:album.title|escapejs }}",
                    public_id: "{{ media.public_id }}" /* ZERO-TRUST ID INJECTED */
} {% if not forloop.last %}, {% endif %}
{% endif %}
{% endfor %}
      ]
    }{% if not forloop.last %}, {% endif %}
{% endfor %}
  };

let activeAlbumKey = null;
let activePhotosList = [];
let currentCarouselIndex = 0;
let isBatchMode = false;
let selectedPhotoSet = new Set();

async function forceDownload(e, url, filename, btnElement, btnId) {
    e.preventDefault();
    const originalText = document.getElementById(btnId).textContent;
    document.getElementById(btnId).textContent = 'Downloading...';

    try {
        const response = await fetch(url);
        const blob = await response.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
        window.open(url, '_blank');
    } finally {
        document.getElementById(btnId).textContent = originalText;
    }
}

const lightboxShareBtn = document.getElementById('lightboxShareBtn');
if (lightboxShareBtn) {
    lightboxShareBtn.addEventListener('click', async () => {
        const photo = activePhotosList[currentCarouselIndex];
        if (!photo) return;

        const deepLinkUrl = window.location.origin + window.location.pathname + '?media=' + photo.public_id;

        if (navigator.share) {
            try {
                await navigator.share({
                    title: photo.caption || 'GCPCUL Media Archive',
                    text: 'Check out this photo from the official GCPCUL Gallery.',
                    url: deepLinkUrl
                });
            } catch (err) {
                console.log('Share cancelled or failed.', err);
            }
        } else {
            // Fallback for desktop browsers that don't have mobile share sheets
            navigator.clipboard.writeText(deepLinkUrl);
            showToast('Link copied to clipboard! Paste to share.', 'success');
        }
    });
}

function updateLightbox(activeImageElement) {
    // 1. Grab the UUID from the thumbnail the user just clicked
    const publicId = activeImageElement.getAttribute('data-public-id');

    // 2. Update the main lightbox image source
    document.getElementById('lightboxMainImage').src = activeImageElement.src;

    // 3. THE ENTERPRISE FIX: Dynamically route the download button
    const downloadBtn = document.getElementById('lightboxBottomDownloadBtn');
    downloadBtn.href = `/src/auth/admin/gallery/media/${publicId}/download/`;
}

/* ALBUM OPEN/CLOSE LOGIC */
function openAlbum(albumKey, updateUrl = true) {
    const data = ALBUMS_DATA[albumKey];
    if (!data) return;

    activeAlbumKey = albumKey;
    activePhotosList = data.photos;

    document.getElementById('openedAlbumTitle').textContent = data.title;
    document.getElementById('openedAlbumSubtitle').textContent = data.subtitle;

    const masonryGrid = document.getElementById('albumPhotosMasonryGrid');
    masonryGrid.innerHTML = '';

    data.photos.forEach((photo, idx) => {
        const item = document.createElement('div');
        item.className = 'photo-item';
        item.setAttribute('data-index', idx);

        const thumbSrc = photo.type === 'video' ? photo.thumb : photo.src;
        const playOverlay = photo.type === 'video' ? `<div class="video-play-indicator"><span class="icon-svg"><span class="material-symbols-outlined" style="font-size:1.8rem;">play_arrow</span></span></div>` : '';

        item.innerHTML = `
          <div class="photo-select-checkbox">✓</div>
          ${playOverlay}
          <img src="${thumbSrc}" alt="${photo.caption}" loading="lazy" onerror="this.style.display='none';">
        `;

        item.addEventListener('click', (e) => {
            if (isBatchMode) {
                e.stopPropagation();
                if (selectedPhotoSet.has(idx)) {
                    selectedPhotoSet.delete(idx);
                    item.classList.remove('selected');
                } else {
                    selectedPhotoSet.add(idx);
                    item.classList.add('selected');
                }
                updateBatchBarStatus();
            } else {
                openCarouselLightbox(idx);
            }
        });

        masonryGrid.appendChild(item);
    });

    document.getElementById('albumsDirectorySection').style.display = 'none';
    document.getElementById('photoGridViewSection').classList.add('active');
    window.scrollTo({ top: document.getElementById('photoGridViewSection').offsetTop - 100, behavior: 'smooth' });

    // ENTERPRISE FIX: Push the raw UUID to the URL bar
    if (updateUrl) {
        window.history.pushState({ album: albumKey }, '', `?album=${albumKey}`);
    }
}

function closeAlbumView(updateUrl = true) {
    document.getElementById('photoGridViewSection').classList.remove('active');
    document.getElementById('albumsDirectorySection').style.display = 'block';

    const lightboxMainVideo = document.getElementById('lightboxMainVideo');
    if (lightboxMainVideo) lightboxMainVideo.pause();

    activeAlbumKey = null;
    activePhotosList = [];
    exitBatchMode();

    // ENTERPRISE FIX: Revert URL when closing the album
    if (updateUrl) {
        window.history.pushState({}, '', window.location.pathname);
    }
}

// Listen for Native Back/Forward button clicks
window.addEventListener('popstate', (e) => {
    const params = new URLSearchParams(window.location.search);
    const albumParam = params.get('album');

    if (albumParam) {
        openAlbum(albumParam, false); // Direct UUID
    } else {
        closeAlbumView(false);
    }
});

/* BATCH MULTI-SELECT DOWNLOAD LOGIC */
const toggleBatchBtn = document.getElementById('toggleBatchModeBtn');
const batchBtnLabel = document.getElementById('batchBtnLabel');
const batchActionBar = document.getElementById('batchActionBar');
const batchSelectedCountText = document.getElementById('batchSelectedCountText');
const downloadBatchGroupBtn = document.getElementById('downloadBatchGroupBtn');

if (toggleBatchBtn) {
    toggleBatchBtn.addEventListener('click', () => {
        if (!activeAlbumKey) {
            showToast('Please open an album first to select photos!', 'warning');
            return;
        }
        isBatchMode ? exitBatchMode() : enterBatchMode();
    });
}

function enterBatchMode() {
    isBatchMode = true;
    document.body.classList.add('batch-mode-active');
    toggleBatchBtn.classList.add('active');
    batchBtnLabel.textContent = 'Cancel Selection';
}

function exitBatchMode() {
    isBatchMode = false;
    document.body.classList.remove('batch-mode-active');
    toggleBatchBtn.classList.remove('active');
    batchBtnLabel.textContent = 'Select Multiple Photos';
    selectedPhotoSet.clear();
    document.querySelectorAll('.photo-item').forEach(el => el.classList.remove('selected'));
    updateBatchBarStatus();
}

function updateBatchBarStatus() {
    const count = selectedPhotoSet.size;
    batchSelectedCountText.textContent = `${count} Media Selected`;

    if (count > 0 && isBatchMode) {
        batchActionBar.classList.add('visible');
    } else {
        batchActionBar.classList.remove('visible');
    }
}

if (downloadBatchGroupBtn) {
    downloadBatchGroupBtn.addEventListener('click', async () => {
        if (selectedPhotoSet.size === 0) return;

        const originalText = document.getElementById('batchDownloadBtnText').textContent;
        document.getElementById('batchDownloadBtnText').textContent = 'Downloading...';

        for (let idx of selectedPhotoSet) {
            const photo = activePhotosList[idx];
            if (photo) {
                const url = `/api/public/media/${photo.public_id}/download/`;
                const a = document.createElement('a');
                a.href = url;
                a.target = '_blank'; // Required to allow multiple simultaneous downloads
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                // Stagger the downloads so browser popup blockers don't panic
                await new Promise(r => setTimeout(r, 600));
            }
        }

        document.getElementById('batchDownloadBtnText').textContent = originalText;
        showToast(`Successfully downloaded ${selectedPhotoSet.size} selected file(s)!`, 'success');
        exitBatchMode();
    });
}

/* HYBRID FULL-SCREEN CAROUSEL LIGHTBOX LOGIC */
const carouselModal = document.getElementById('carouselLightboxModal');
const lightboxMainImg = document.getElementById('lightboxMainImg');
const lightboxMainVideo = document.getElementById('lightboxMainVideo');
const lightboxCaptionText = document.getElementById('lightboxCaptionText');
const lightboxIndexIndicator = document.getElementById('lightboxIndexIndicator');
const lightboxAlbumTag = document.getElementById('lightboxAlbumTag');
const lightboxBottomDownloadBtn = document.getElementById('lightboxBottomDownloadBtn');
const lightboxCloseBtn = document.getElementById('lightboxCloseBtn');
const carouselPrevBtn = document.getElementById('carouselPrevBtn');
const carouselNextBtn = document.getElementById('carouselNextBtn');

function openCarouselLightbox(index) {
    if (!activePhotosList || activePhotosList.length === 0) return;
    currentCarouselIndex = index;
    updateCarouselStage();
    carouselModal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function updateCarouselStage() {
    const media = activePhotosList[currentCarouselIndex];
    const albumObj = ALBUMS_DATA[activeAlbumKey];
    if (!media) return;

    lightboxMainVideo.pause();
    lightboxMainVideo.src = '';
    lightboxMainImg.src = '';

    if (media.type === 'video') {
        lightboxMainImg.classList.remove('active');
        lightboxMainVideo.classList.add('active');
        lightboxMainVideo.src = media.src;
        lightboxMainVideo.play().catch(e => console.log("Auto-play prevented"));
    } else {
        lightboxMainVideo.classList.remove('active');
        lightboxMainImg.classList.add('active');
        lightboxMainImg.src = media.src;
    }

    lightboxCaptionText.textContent = media.caption;
    lightboxIndexIndicator.textContent = `Media ${currentCarouselIndex + 1} of ${activePhotosList.length}`;
    if (albumObj) lightboxAlbumTag.textContent = albumObj.title;

    lightboxBottomDownloadBtn.href = `/api/public/media/${media.public_id}/download/`;
    lightboxBottomDownloadBtn.removeAttribute('onclick');
}

function closeCarouselLightbox() {
    carouselModal.classList.remove('active');
    document.body.style.overflow = 'auto';
    lightboxMainVideo.pause();
}

if (carouselPrevBtn) {
    carouselPrevBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        currentCarouselIndex = (currentCarouselIndex - 1 + activePhotosList.length) % activePhotosList.length;
        updateCarouselStage();
    });
}

if (carouselNextBtn) {
    carouselNextBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        currentCarouselIndex = (currentCarouselIndex + 1) % activePhotosList.length;
        updateCarouselStage();
    });
}

if (lightboxCloseBtn) lightboxCloseBtn.addEventListener('click', closeCarouselLightbox);

document.addEventListener('keydown', (e) => {
    if (!carouselModal.classList.contains('active')) return;
    if (e.key === 'ArrowLeft') {
        currentCarouselIndex = (currentCarouselIndex - 1 + activePhotosList.length) % activePhotosList.length;
        updateCarouselStage();
    } else if (e.key === 'ArrowRight') {
        currentCarouselIndex = (currentCarouselIndex + 1) % activePhotosList.length;
        updateCarouselStage();
    } else if (e.key === 'Escape') {
        closeCarouselLightbox();
    }
});

/* DIRECTORY CATEGORY FILTERING */
const filterBtns = document.querySelectorAll('#categoryFilterBar .filter-tab-btn');
const albumCards = document.querySelectorAll('.album-card');
const albumEmptyState = document.getElementById('albumEmptyState');

if (filterBtns) {
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (activeAlbumKey) closeAlbumView();

            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const category = btn.getAttribute('data-filter');
            let visibleCount = 0;

            albumCards.forEach(card => {
                const cardCat = card.getAttribute('data-category');
                if (category === 'all' || cardCat === category) {
                    card.style.display = 'block';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            if (visibleCount === 0) {
                albumEmptyState.classList.add('active');
            } else {
                albumEmptyState.classList.remove('active');
            }
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const sharedMediaId = params.get('media');
    const sharedAlbumId = params.get('album');

    // Open Album via UUID
    if (sharedAlbumId && ALBUMS_DATA[sharedAlbumId]) {
        openAlbum(sharedAlbumId, false);
    }

    // Open specific Media via UUID
    if (sharedMediaId) {
        for (const [albumKey, albumData] of Object.entries(ALBUMS_DATA)) {
            const photoIdx = albumData.photos.findIndex(p => p.public_id === sharedMediaId);

            if (photoIdx !== -1) {
                openAlbum(albumKey, false);

                setTimeout(() => {
                    openCarouselLightbox(photoIdx);
                }, 300);

                window.history.replaceState({}, document.title, window.location.pathname);
                break;
            }
        }
    }
});
