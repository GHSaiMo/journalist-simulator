/**
 * Pure-icon, zero-text Photo Album & Native Share / Clipboard / Download manager
 * backed by IndexedDB so captured shots persist across sessions on PC & Mobile.
 */

const DB_NAME = 'press_sim_album_db';
const STORE_NAME = 'photos';

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export class AlbumManager {
  constructor({ onOpenChange }) {
    this.photos = []; // { id, dataUrl, focalMm, distM, ts }
    this.isOpen = false;
    this.activeIdx = -1;
    this.onOpenChange = onOpenChange;

    this.modalEl = document.getElementById('album-modal');
    this.gridEl = document.getElementById('album-grid');
    this.emptyIconEl = document.getElementById('album-empty-icon');
    this.lightboxEl = document.getElementById('album-lightbox');
    this.lightboxImg = document.getElementById('lightbox-img');
    this.lightboxExif = document.getElementById('lightbox-exif');
    this.countBadge = document.getElementById('album-count');
    this.thumbPreview = document.getElementById('album-thumb-preview');
    this.flyContainer = document.getElementById('photo-fly-layer');

    this._bindEvents();
    this._loadStored();
  }

  async _loadStored() {
    try {
      const db = await openDB();
      const tx = db.transaction(STORE_NAME, 'readonly');
      const req = tx.objectStore(STORE_NAME).getAll();
      req.onsuccess = () => {
        const items = (req.result || []).sort((a, b) => b.ts - a.ts);
        this.photos = items;
        this._syncBadge();
      };
    } catch (_) {
      // Fallback to in-memory if IndexedDB blocked in private mode
    }
  }

  async _saveToDB(item) {
    try {
      const db = await openDB();
      const tx = db.transaction(STORE_NAME, 'readwrite');
      tx.objectStore(STORE_NAME).put(item);
    } catch (_) {}
  }

  async _deleteFromDB(id) {
    try {
      const db = await openDB();
      const tx = db.transaction(STORE_NAME, 'readwrite');
      tx.objectStore(STORE_NAME).delete(id);
    } catch (_) {}
  }

  _syncBadge() {
    if (this.countBadge) {
      this.countBadge.textContent = String(this.photos.length);
      this.countBadge.style.display = this.photos.length > 0 ? 'flex' : 'none';
    }
    if (this.thumbPreview) {
      if (this.photos.length > 0) {
        this.thumbPreview.style.backgroundImage = `url(${this.photos[0].dataUrl})`;
        this.thumbPreview.classList.add('has-photo');
      } else {
        this.thumbPreview.style.backgroundImage = '';
        this.thumbPreview.classList.remove('has-photo');
      }
    }
  }

  addPhoto({ dataUrl, focalMm, fStop = 2.8, distM }) {
    const item = {
      id: `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      dataUrl,
      focalMm: Math.round(focalMm),
      fStop: Number(fStop),
      distM: Number(distM.toFixed(1)),
      ts: Date.now(),
    };
    this.photos.unshift(item);
    if (this.photos.length > 48) {
      const dropped = this.photos.pop();
      this._deleteFromDB(dropped.id);
    }
    this._saveToDB(item);
    this._syncBadge();
    this._animateFlyThumbnail(dataUrl);
    return item;
  }

  _animateFlyThumbnail(dataUrl) {
    if (!this.flyContainer) return;
    const card = document.createElement('div');
    card.className = 'flying-polaroid';
    card.style.backgroundImage = `url(${dataUrl})`;
    this.flyContainer.appendChild(card);

    requestAnimationFrame(() => {
      card.classList.add('fly-to-corner');
    });
    setTimeout(() => card.remove(), 720);
  }

  open() {
    this.isOpen = true;
    this.activeIdx = -1;
    this._renderGrid();
    this.lightboxEl.classList.add('hidden');
    this.modalEl.classList.remove('hidden');
    if (this.onOpenChange) this.onOpenChange(true);
  }

  close() {
    this.isOpen = false;
    this.activeIdx = -1;
    this.modalEl.classList.add('hidden');
    this.lightboxEl.classList.add('hidden');
    if (this.onOpenChange) this.onOpenChange(false);
  }

  toggle() {
    if (this.isOpen) this.close();
    else this.open();
  }

  _renderGrid() {
    this.gridEl.innerHTML = '';
    if (this.photos.length === 0) {
      this.emptyIconEl.classList.remove('hidden');
      return;
    }
    this.emptyIconEl.classList.add('hidden');

    this.photos.forEach((p, idx) => {
      const fStr = (p.fStop || 2.8).toFixed(p.fStop >= 10 ? 0 : 1);
      const cell = document.createElement('button');
      cell.className = 'album-cell';
      cell.innerHTML = `
        <div class="album-cell-img" style="background-image:url(${p.dataUrl})"></div>
        <div class="album-cell-meta"><span>${p.focalMm}</span><span>F${fStr}</span></div>
      `;
      cell.addEventListener('click', () => this._openLightbox(idx));
      this.gridEl.appendChild(cell);
    });
  }

  _openLightbox(idx) {
    if (idx < 0 || idx >= this.photos.length) return;
    this.activeIdx = idx;
    const p = this.photos[idx];
    const fStr = (p.fStop || 2.8).toFixed(p.fStop >= 10 ? 0 : 1);
    this.lightboxImg.src = p.dataUrl;
    this.lightboxExif.textContent = `${p.focalMm}  ·  F${fStr}  ·  ${idx + 1}/${this.photos.length}`;
    this.lightboxEl.classList.remove('hidden');
  }

  _stepLightbox(dir) {
    if (this.photos.length === 0) return;
    const next = (this.activeIdx + dir + this.photos.length) % this.photos.length;
    this._openLightbox(next);
  }

  async _dataUrlToBlob(dataUrl) {
    const res = await fetch(dataUrl);
    return await res.blob();
  }

  _flashBtnSuccess(btn) {
    btn.classList.add('action-ok');
    setTimeout(() => btn.classList.remove('action-ok'), 900);
  }

  async shareCurrent(btn) {
    const p = this.photos[this.activeIdx];
    if (!p) return;
    try {
      const blob = await this._dataUrlToBlob(p.dataUrl);
      const file = new File([blob], `shot_${p.focalMm}_${p.id.slice(-4)}.png`, { type: 'image/png' });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file] });
        this._flashBtnSuccess(btn);
        return;
      }
    } catch (e) {
      if (e && e.name === 'AbortError') return;
    }
    // Desktop fallback: try clipboard copy first, else download
    const copied = await this.copyCurrent(btn);
    if (!copied) this.downloadCurrent(btn);
  }

  async copyCurrent(btn) {
    const p = this.photos[this.activeIdx];
    if (!p) return false;
    try {
      if (navigator.clipboard && window.ClipboardItem) {
        const blob = await this._dataUrlToBlob(p.dataUrl);
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
        this._flashBtnSuccess(btn);
        return true;
      }
    } catch (_) {}
    return false;
  }

  downloadCurrent(btn) {
    const p = this.photos[this.activeIdx];
    if (!p) return;
    const a = document.createElement('a');
    a.href = p.dataUrl;
    a.download = `shot_${p.focalMm}_${p.id.slice(-4)}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    if (btn) this._flashBtnSuccess(btn);
  }

  deleteCurrent() {
    const p = this.photos[this.activeIdx];
    if (!p) return;
    this.photos.splice(this.activeIdx, 1);
    this._deleteFromDB(p.id);
    this._syncBadge();
    if (this.photos.length === 0) {
      this.lightboxEl.classList.add('hidden');
      this._renderGrid();
    } else {
      const nextIdx = Math.min(this.activeIdx, this.photos.length - 1);
      this._renderGrid();
      this._openLightbox(nextIdx);
    }
  }

  _bindEvents() {
    document.getElementById('btn-open-album')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggle();
    });
    document.getElementById('btn-close-album')?.addEventListener('click', () => this.close());
    document.getElementById('btn-close-lightbox')?.addEventListener('click', () => {
      this.lightboxEl.classList.add('hidden');
      this.activeIdx = -1;
    });
    document.getElementById('btn-prev-photo')?.addEventListener('click', () => this._stepLightbox(-1));
    document.getElementById('btn-next-photo')?.addEventListener('click', () => this._stepLightbox(1));

    const btnShare = document.getElementById('btn-share-photo');
    btnShare?.addEventListener('click', () => this.shareCurrent(btnShare));

    const btnCopy = document.getElementById('btn-copy-photo');
    btnCopy?.addEventListener('click', () => this.copyCurrent(btnCopy));

    const btnDl = document.getElementById('btn-download-photo');
    btnDl?.addEventListener('click', () => this.downloadCurrent(btnDl));

    document.getElementById('btn-delete-photo')?.addEventListener('click', () => this.deleteCurrent());

    // Keyboard shortcuts while album is open
    window.addEventListener('keydown', (e) => {
      if (!this.isOpen) return;
      if (e.code === 'Escape') {
        if (this.activeIdx >= 0) {
          this.lightboxEl.classList.add('hidden');
          this.activeIdx = -1;
        } else {
          this.close();
        }
      } else if (this.activeIdx >= 0) {
        if (e.code === 'ArrowLeft') this._stepLightbox(-1);
        if (e.code === 'ArrowRight') this._stepLightbox(1);
      }
    });

    // Touch swipe left/right inside lightbox on mobile
    let touchStartX = null;
    this.lightboxEl?.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) touchStartX = e.touches[0].clientX;
    }, { passive: true });
    this.lightboxEl?.addEventListener('touchend', (e) => {
      if (touchStartX === null) return;
      const dx = e.changedTouches[0].clientX - touchStartX;
      touchStartX = null;
      if (Math.abs(dx) > 48) {
        this._stepLightbox(dx < 0 ? 1 : -1);
      }
    }, { passive: true });
  }
}
