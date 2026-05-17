/* app.js — shared utilities: clock, toast, modal */

// ── Clock ──────────────────────────────────────────────────────────────
function updateClock() {
  const now  = new Date();
  const date = now.toLocaleDateString('en-IN', {weekday:'short', month:'short', day:'numeric'});
  const time = now.toLocaleTimeString('en-IN', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
  const dateEl = document.getElementById('tb-date');
  const timeEl = document.getElementById('tb-time');
  if (dateEl) dateEl.textContent = date;
  if (timeEl) timeEl.textContent = time;
}
setInterval(updateClock, 1000);
updateClock();

function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}

// ── Toast ──────────────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const map = { success:'t-success', error:'t-error', warning:'t-warning', info:'t-info' };
  const icons = {
    success: '✓',
    error:   '✕',
    warning: '⚠',
    info:    'ℹ',
  };

  const toast = document.createElement('div');
  toast.className = `toast ${map[type] || 't-info'}`;
  toast.innerHTML = `
    <span style="font-size:.85rem;flex-shrink:0">${icons[type] || 'ℹ'}</span>
    <div>${message}</div>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideOut .2s ease forwards';
    setTimeout(() => toast.remove(), 200);
  }, duration);
}

// ── Modal ──────────────────────────────────────────────────────────────
function closeModal() {
  const m = document.getElementById('del-modal');
  if (m) m.style.display = 'none';
}
// Close on overlay click
document.addEventListener('click', e => {
  if (e.target.id === 'del-modal') closeModal();
});
// Close on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

// ── Theme ──────────────────────────────────────────────────────────────
function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const newTheme = current === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', newTheme);
  localStorage.setItem('faceid_theme', newTheme);
  updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
  const text = document.getElementById('theme-text');
  const icon = document.getElementById('theme-icon');
  if (text) text.textContent = theme === 'light' ? 'Dark Mode' : 'Light Mode';
  if (icon) {
    if (theme === 'light') {
      icon.innerHTML = `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>`;
    } else {
      icon.innerHTML = `<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>`;
    }
  }
}

// ── Voice ──────────────────────────────────────────────────────────────
function speak(text) {
  if (!window.speechSynthesis) return;
  
  // Cancel existing to prevent backlog if many people check in at once
  window.speechSynthesis.cancel();
  
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  utterance.volume = 1.0;
  
  // Try to find a good female/natural voice
  const voices = window.speechSynthesis.getVoices();
  if (voices.length > 0) {
    utterance.voice = voices.find(v => v.name.includes('Female') || v.name.includes('Google')) || voices[0];
  }
  
  window.speechSynthesis.speak(utterance);
}

// ── Geofencing ──────────────────────────────────────────────────────────
async function checkLocation(officeLat, officeLon, radius) {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      showToast('Geolocation is not supported by your browser', 'error');
      return resolve(false);
    }

    navigator.geolocation.getCurrentPosition(
      pos => {
        const dist = getDistanceFromLatLonInM(
          pos.coords.latitude, pos.coords.longitude,
          officeLat, officeLon
        );
        if (dist > radius) {
          showToast(`Outside office area! (${Math.round(dist)}m away)`, 'error');
          resolve(false);
        } else {
          resolve(true);
        }
      },
      err => {
        showToast('Please enable location access to continue', 'warning');
        resolve(false);
      },
      { enableHighAccuracy: true }
    );
  });
}

function getDistanceFromLatLonInM(lat1, lon1, lat2, lon2) {
  const R = 6371e3; // Radius of the earth in meters
  const dLat = deg2rad(lat2 - lat1);
  const dLon = deg2rad(lon2 - lon1);
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function deg2rad(deg) { return deg * (Math.PI / 180); }

// Init theme immediately
const savedTheme = localStorage.getItem('faceid_theme') || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);
document.addEventListener('DOMContentLoaded', () => {
    updateThemeIcon(savedTheme);
    // Needed for Chrome to load voices
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    }
});

// ── Browser Camera Fallback ───────────────────────────────────────────
let fallbackStreams = {};
let fallbackIntervals = {};

function setupClientCameraFallback(imgElementId, mode = 'entry') {
  const imgEl = document.getElementById(imgElementId);
  if (!imgEl) return;
  
  // Prevent duplicate streams/intervals for same element
  if (fallbackIntervals[imgElementId]) return;

  console.log(`Starting client-side webcam fallback for ${imgElementId} (${mode})...`);
  
  // Create hidden video element if not exists
  let videoId = `fallback-video-${imgElementId}`;
  let videoEl = document.getElementById(videoId);
  if (!videoEl) {
    videoEl = document.createElement('video');
    videoEl.id = videoId;
    videoEl.autoplay = true;
    videoEl.playsInline = true;
    videoEl.style.display = 'none';
    document.body.appendChild(videoEl);
  }
  
  // Create hidden canvas element if not exists
  let canvasId = `fallback-canvas-${imgElementId}`;
  let canvasEl = document.getElementById(canvasId);
  if (!canvasEl) {
    canvasEl = document.createElement('canvas');
    canvasEl.id = canvasId;
    canvasEl.width = 640;
    canvasEl.height = 480;
    canvasEl.style.display = 'none';
    document.body.appendChild(canvasEl);
  }

  // Request browser camera stream
  navigator.mediaDevices.getUserMedia({ 
    video: { 
      width: { ideal: 640 }, 
      height: { ideal: 480 },
      facingMode: "user" 
    } 
  })
  .then(stream => {
    fallbackStreams[imgElementId] = stream;
    videoEl.srcObject = stream;
    
    // Periodically capture frames, send to Flask, and update img element
    const ctx = canvasEl.getContext('2d');
    fallbackIntervals[imgElementId] = setInterval(() => {
      if (videoEl.readyState === videoEl.HAVE_ENOUGH_DATA) {
        ctx.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);
        const dataUrl = canvasEl.toDataURL('image/jpeg', 0.80);
        
        fetch('/process_frame_client', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: dataUrl, mode: mode })
        })
        .then(res => res.json())
        .then(resData => {
          if (resData.status === 'ok') {
            imgEl.src = resData.image;
          }
        })
        .catch(err => console.error("Error pushing client-side frame:", err));
      }
    }, 330); // ~3 frames per second to be gentle on server CPU / network
    
    showToast(`Webcam fallback activated for ${mode} gate`, 'success');
  })
  .catch(err => {
    console.error("Could not access browser camera:", err);
    showToast("Please allow camera access to run the demo!", "error");
  });
}

