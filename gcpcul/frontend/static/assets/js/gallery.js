const WORKER_URL = "https://gcpculgh-zip-worker.gcpculgh-zip.workers.dev";

function showToast(message, type = 'success') {
    const toast = document.getElementById('toastNotification');
    const iconSvg = type === 'success'
        ? '<span class="material-symbols-outlined">check_circle</span>'
        : '<span class="material-symbols-outlined">warning</span>';
    toast.className = `toast-notification toast-${type} show`;
    toast.innerHTML = `<span class="icon-svg toast-icon">${iconSvg}</span><span>${message}</span>`;
    setTimeout(() => { toast.classList.remove('show'); }, 3500);
}

let activeAlbumKey = null;
let activePhotosList = [];
let currentCarouselIndex = 0;
let isBatchMode = false;
let selectedPhotoSet = new Set();

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
            } catch (err) { /* cancelled */ }
        } else {
            navigator.clipboard.writeText(deepLinkUrl);
            showToast('Link copied to clipboard!', 'success');
        }
    });
}

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
    if (updateUrl) window.history.pushState({ album: albumKey }, '', `/gallery/${albumKey}/`);
}

function closeAlbumView(updateUrl = true) {
    document.getElementById('photoGridViewSection').classList.remove('active');
    document.getElementById('albumsDirectorySection').style.display = 'block';
    const v = document.getElementById('lightboxMainVideo');
    if (v) v.pause();
    activeAlbumKey = null;
    activePhotosList = [];
    exitBatchMode();
    if (updateUrl) window.history.pushState({}, '', '/gallery/');
}

window.addEventListener('popstate', () => {
    const parts = window.location.pathname.split('/').filter(p => p);
    if (parts[0] === 'gallery' && parts.length > 1) {
        if (ALBUMS_DATA[parts[1]]) openAlbum(parts[1], false);
    } else {
        closeAlbumView(false);
    }
});

const toggleBatchBtn = document.getElementById('toggleBatchModeBtn');
const batchBtnLabel = document.getElementById('batchBtnLabel');
const batchActionBar = document.getElementById('batchActionBar');
const batchSelectedCountText = document.getElementById('batchSelectedCountText');
const downloadBatchGroupBtn = document.getElementById('downloadBatchGroupBtn');

if (toggleBatchBtn) {
    toggleBatchBtn.addEventListener('click', () => {
        if (!activeAlbumKey) {
            showToast('Open an album first to select photos!', 'warning');
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
    batchActionBar.classList.toggle('visible', count > 0 && isBatchMode);
}



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
    if (!activePhotosList.length) return;
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
        lightboxMainVideo.play().catch(() => {});
    } else {
        lightboxMainVideo.classList.remove('active');
        lightboxMainImg.classList.add('active');
        lightboxMainImg.src = media.src;
    }
    lightboxCaptionText.textContent = media.caption;
    lightboxIndexIndicator.textContent = `Media ${currentCarouselIndex + 1} of ${activePhotosList.length}`;
    if (albumObj) lightboxAlbumTag.textContent = albumObj.title;
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

async function requestToken(keys) {
    const res = await fetch('/api/gallery/download-token/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keys }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'Auth failed');
    }
    return res.json();
}

async function downloadFromWorker(keys, filename, displayExt, preFetchedAuth = null) {
    const auth = preFetchedAuth || await requestToken(keys);
    const { token, timestamp } = auth;

    const res = await fetch(WORKER_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keys, filename, token, timestamp }),
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'Download failed');
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}${displayExt || '.zip'}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
}

if (downloadBatchGroupBtn) {
    downloadBatchGroupBtn.addEventListener('click', async () => {
        if (selectedPhotoSet.size === 0) return;
        const btnText = document.getElementById('batchDownloadBtnText');
        const submitBtn = document.getElementById('downloadBatchGroupBtn');
        const originalText = btnText.textContent;
        submitBtn.disabled = true;

        const keys = [...selectedPhotoSet].map(i => activePhotosList[i].r2_key);
        const albumName = activeAlbumKey || 'gallery';

        try {
            btnText.textContent = 'Authenticating...';
            const authData = await requestToken(keys);
            btnText.textContent = 'Building archive...';
            await downloadFromWorker(keys, `${albumName}_selection`, '.zip', authData);
            showToast(`${keys.length} media downloaded!`, 'success');
            exitBatchMode();
        } catch (err) {
            console.error('Batch:', err);
            showToast(err.message || 'Download failed.', 'warning');
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = originalText;
        }
    });
}

if (lightboxBottomDownloadBtn) {
    lightboxBottomDownloadBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        const media = activePhotosList[currentCarouselIndex];
        if (!media) return;
        const btnText = document.getElementById('bottomDownloadBtnText');
        const originalText = btnText.textContent;
        btnText.textContent = 'Downloading...';

        try {
            const ext = media.type === 'video' ? 'mp4' : 'webp';
            await downloadFromWorker(
                [media.r2_key],
                media.public_id.slice(0, 8),
                `.${ext}`
            );
        } catch (err) {
            console.error('Download:', err);
            showToast('Download failed.', 'warning');
        } finally {
            btnText.textContent = originalText;
        }
    });
}   

const filterBtns = document.querySelectorAll('#categoryFilterBar .filter-tab-btn');
const albumCards = document.querySelectorAll('.album-card');
const albumEmptyState = document.getElementById('albumEmptyState');
if (filterBtns) {
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (activeAlbumKey) closeAlbumView();
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const cat = btn.getAttribute('data-filter');
            let visible = 0;
            albumCards.forEach(card => {
                const show = cat === 'all' || card.getAttribute('data-category') === cat;
                card.style.display = show ? 'block' : 'none';
                if (show) visible++;
            });
            albumEmptyState.classList.toggle('active', visible === 0);
        });
    });
}

function initGalleryScripts() {
    if (typeof TARGET_ALBUM !== 'undefined' && TARGET_ALBUM !== '') {
        if (ALBUMS_DATA[TARGET_ALBUM]) setTimeout(() => openAlbum(TARGET_ALBUM, false), 50);
    }
    const params = new URLSearchParams(window.location.search);
    const sharedMediaId = params.get('media');
    if (sharedMediaId) {
        for (const [key, data] of Object.entries(ALBUMS_DATA)) {
            const idx = data.photos.findIndex(p => p.public_id === sharedMediaId);
            if (idx !== -1) {
                openAlbum(key, false);
                setTimeout(() => openCarouselLightbox(idx), 300);
                window.history.replaceState({}, document.title, `/gallery/${key}/`);
                break;
            }
        }
    }
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGalleryScripts);
} else {
    initGalleryScripts();
}   