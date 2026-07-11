// ─────────────────────────────────────────────────────
// FLEEK COMPANION – app.js  (v3)
// Pages: 0=welcome 1=register 2=connect 3=enrich 4=success
// API: fleek-onboarding/backend (FastAPI) @ localhost:8000 — same origin when
//      the backend serves this folder at http://localhost:8000/
// ─────────────────────────────────────────────────────

const API_BASE    = window.location.port === '8000' ? '' : 'http://localhost:8000';

const PAGES = [
  'page-welcome',
  'page-register',
  'page-connect',
  'page-enrich',
  'page-success',
];

// ── App State ──────────────────────────────────────────
const state = {
  currentPage: 0,
  user: { firstName: '', lastName: '', email: '' },
  emailVerified: false,
  connectedPlatforms: { ebay: false, shopify: false, vinted: false },
  shopifyDomain: null,
  vintedSellerId: null,
  importedData: { orders: 0, items: 0, platforms: [] },
  sellerId: null,        // set by POST /onboard
  profile: null,         // seller profile from the backend

  // Enrich
  images: [],           // { file, dataUrl }
  sheetFile: null,      // File
  voiceBlob: null,      // Blob
  voiceDuration: 0,
  prefsText: '',

  // Recording internals
  mediaRecorder: null,
  recordingChunks: [],
  recordingInterval: null,
  recordingSeconds: 0,
  isRecording: false,
};

// ── Navigation ─────────────────────────────────────────
function goToPage(index) {
  if (index < 0 || index >= PAGES.length) return;
  document.getElementById(PAGES[state.currentPage])?.classList.remove('active');
  document.getElementById(PAGES[index])?.classList.add('active');
  state.currentPage = index;
  updateStepDots(index);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updateStepDots(pageIndex) {
  // Steps shown for pages 1-5 (step 0 = register, step 4 = success)
  const dots  = document.querySelectorAll('.step-dot');
  const lines = document.querySelectorAll('.step-line');
  const si = pageIndex - 1;
  dots.forEach((d, i) => {
    d.classList.remove('active', 'done');
    if (i < si) d.classList.add('done');
    else if (i === si) d.classList.add('active');
  });
  lines.forEach((l, i) => l.classList.toggle('done', i < si));
}

// ── PAGE 1: REGISTER ──────────────────────────────────
async function handleRegister(e) {
  e.preventDefault();
  state.user.firstName    = document.getElementById('firstName').value.trim();
  state.user.lastName     = document.getElementById('lastName').value.trim();
  state.user.email        = document.getElementById('email').value.trim();
  state.user.businessName = document.getElementById('businessName')?.value.trim() || '';
  state.user.sellerType   = document.getElementById('sellerType')?.value || '';

  showToast(`Welcome to Fleek, ${state.user.firstName}`, 'success');
  goToPage(2); // straight to connect stores
}

function togglePassword() {
  const input = document.getElementById('password');
  const icon  = document.getElementById('eyeIcon');
  const hide  = input.type === 'password';
  input.type  = hide ? 'text' : 'password';
  icon.innerHTML = hide
    ? '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>'
    : '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
}

// ── PAGE 3: CONNECT STORES ─────────────────────────────
async function connectEbay() {
  const btn = document.getElementById('ebayConnectBtn');
  btn.classList.add('loading');
  btn.textContent = 'Connecting…';
  await simulateOAuth();
  setPlatformConnected('ebay');
  showToast('eBay connected!', 'success');
}

async function connectShopify() {
  const raw = document.getElementById('shopDomain').value.trim();
  if (!raw) { document.getElementById('shopDomain').focus(); showToast('Enter your Shopify store name', 'error'); return; }

  // "mock" runs the whole flow against the backend's built-in demo shop
  const domain = raw.toLowerCase() === 'mock' ? 'mock' : raw.replace(/\.myshopify\.com$/i, '') + '.myshopify.com';
  state.shopifyDomain = domain;
  document.getElementById('shopifyDomainLabel').textContent = domain;

  // Already connected (token stored server-side)?
  try {
    const st = await (await fetch(`${API_BASE}/shopify/status?shop=${encodeURIComponent(domain)}`)).json();
    if (st.connected) {
      setPlatformConnected('shopify');
      showToast(`Shopify store "${domain}" connected!`, 'success');
      return;
    }
    if (!st.oauth_configured) {
      showToast('Shopify OAuth keys not set in backend/.env yet — type "mock" to use the demo shop', 'error');
      return;
    }
  } catch {
    showToast('Backend unreachable at ' + (API_BASE || window.location.origin), 'error');
    return;
  }

  // Real OAuth: popup to Shopify's consent screen, then poll until the
  // backend callback has stored the token
  window.open(`${API_BASE}/connect/shopify?shop=${encodeURIComponent(domain)}`, 'shopify-oauth', 'width=600,height=760');
  showToast('Approve the app in the Shopify window…', 'info');

  for (let i = 0; i < 60; i++) {
    await sleep(2000);
    try {
      const st = await (await fetch(`${API_BASE}/shopify/status?shop=${encodeURIComponent(domain)}`)).json();
      if (st.connected) {
        setPlatformConnected('shopify');
        showToast(`Shopify store "${domain}" connected!`, 'success');
        return;
      }
    } catch {}
  }
  showToast('Shopify connection timed out — try again', 'error');
}

async function connectVinted() {
  const url = document.getElementById('vintedUrl').value.trim();
  if (!url) { document.getElementById('vintedUrl').focus(); showToast('Enter your Vinted profile URL', 'error'); return; }
  const match = url.match(/\/member\/(\d+)/);
  if (!match) { showToast('Invalid Vinted URL. Example: https://www.vinted.co.uk/member/12345-username', 'error'); return; }
  state.vintedSellerId = match[1];
  document.getElementById('vintedLabel').textContent = `Vinted seller #${state.vintedSellerId}`;

  try {
    await fetchWithFallback(`${API_BASE}/connect/vinted`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile_url: url }),
    }, { status: 'connected' });
  } catch {}
  setPlatformConnected('vinted');
  showToast('Vinted profile connected!', 'success');
}

function setPlatformConnected(platform) {
  state.connectedPlatforms[platform] = true;
  document.getElementById(`${platform}Body`).style.display = 'none';
  document.getElementById(`${platform}Connected`).style.display = 'flex';
  document.getElementById(`${platform}Card`).classList.add('connected-state');
  document.getElementById(`${platform}Status`).className = 'status-badge status-connected';
  document.getElementById(`${platform}Status`).textContent = '✓ Connected';
  updateImportButton();
}

function disconnectPlatform(platform) {
  state.connectedPlatforms[platform] = false;
  document.getElementById(`${platform}Body`).style.display = 'flex';
  document.getElementById(`${platform}Connected`).style.display = 'none';
  document.getElementById(`${platform}Card`).classList.remove('connected-state');
  document.getElementById(`${platform}Status`).className = 'status-badge status-not-connected';
  document.getElementById(`${platform}Status`).textContent = 'Not connected';
  if (platform === 'ebay') {
    const btn = document.getElementById('ebayConnectBtn');
    btn.classList.remove('loading');
    btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>Connect eBay`;
  }
  updateImportButton();
  showToast(`${platform.charAt(0).toUpperCase() + platform.slice(1)} disconnected`, 'info');
}

function updateImportButton() {
  const any = Object.values(state.connectedPlatforms).some(Boolean);
  document.getElementById('importBtn').disabled = !any;
}

// ── IMPORT with animated progress ─────────────────────
async function startImportAndProceed() {
  const btn = document.getElementById('importBtn');
  btn.disabled = true;

  const progress  = document.getElementById('importProgress');
  const fill      = document.getElementById('progressFill');
  const label     = document.getElementById('importProgressLabel');
  const sub       = document.getElementById('importProgressSub');
  progress.style.display = 'flex';

  // Animated progress phases
  const phases = [
    { pct: 20, msg: 'Authenticating with your stores…',   sub: 'Verifying OAuth tokens' },
    { pct: 45, msg: 'Fetching order history…',             sub: 'Pulling orders from connected platforms' },
    { pct: 70, msg: 'Processing listings…',                sub: 'Normalising product data' },
    { pct: 90, msg: 'Finalising import…',                  sub: 'Almost there!' },
  ];

  for (const phase of phases) {
    fill.style.width = phase.pct + '%';
    label.textContent = phase.msg;
    sub.textContent   = phase.sub;
    await sleep(700);
  }

  // Real counts from the backend (Shopify is the live integration;
  // eBay/Vinted stay visual-only for now)
  let totalOrders = 0, totalItems = 0;
  const connectedList = [];
  if (state.connectedPlatforms.shopify && state.shopifyDomain) {
    const preview = await fetchWithFallback(
      `${API_BASE}/shopify/preview?shop=${encodeURIComponent(state.shopifyDomain)}`,
      {}, { orders: 0, items: 0 }
    );
    totalOrders += preview.orders;
    totalItems  += preview.items;
    connectedList.push('shopify');
  }
  ['ebay', 'vinted'].forEach(p => { if (state.connectedPlatforms[p]) connectedList.push(p); });
  state.importedData = { orders: totalOrders, items: totalItems, platforms: connectedList };

  fill.style.width = '100%';
  label.textContent = `Import complete — ${totalOrders} orders, ${totalItems} listings`;
  sub.textContent = '';
  await sleep(600);
  progress.style.display = 'none';

  // Update enrich page chip
  const platforms = connectedList.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(', ');
  document.getElementById('importSummaryText').textContent =
    `${totalOrders} orders & ${totalItems} listings imported from ${platforms || 'connected stores'}`;

  showToast(`✓ Imported ${totalOrders} orders from ${connectedList.length} store${connectedList.length !== 1 ? 's' : ''}`, 'success');
  goToPage(4);
}

// ── PAGE 4: ENRICH ─────────────────────────────────────

// --- Images ---
function handleDragOver(e) {
  e.preventDefault();
  e.currentTarget.classList.add('drag-over');
}
function handleDragLeave(e) {
  e.currentTarget.classList.remove('drag-over');
}
function handleImageDrop(e) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const files = [...e.dataTransfer.files].filter(f => f.type.startsWith('image/'));
  processImages(files);
}
function handleImageSelect(e) {
  processImages([...e.target.files]);
  e.target.value = '';
}
function processImages(files) {
  files.forEach(file => {
    const reader = new FileReader();
    reader.onload = ev => {
      state.images.push({ file, dataUrl: ev.target.result });
      renderImagePreviews();
    };
    reader.readAsDataURL(file);
  });
}
function renderImagePreviews() {
  const grid = document.getElementById('imagePreviewGrid');
  const inner = document.querySelector('.drop-zone-inner');

  if (state.images.length > 0) {
    inner.style.display = 'none';
  }

  grid.innerHTML = state.images.map((img, i) => `
    <div class="image-thumb" id="thumb-${i}">
      <img src="${img.dataUrl}" alt="upload ${i + 1}" />
      <div class="image-thumb-remove" onclick="removeImage(${i})">✕</div>
    </div>
  `).join('');

  document.getElementById('imageCount').textContent =
    `${state.images.length} uploaded`;
}
function removeImage(index) {
  state.images.splice(index, 1);
  if (state.images.length === 0) {
    document.querySelector('.drop-zone-inner').style.display = 'flex';
  }
  renderImagePreviews();
}

// --- Spreadsheet ---
function handleSheetDrop(e) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const files = [...e.dataTransfer.files].filter(f =>
    f.name.match(/\.(xlsx|xls|csv)$/i));
  if (files.length) processSheet(files[0]);
}
function handleSheetSelect(e) {
  if (e.target.files[0]) processSheet(e.target.files[0]);
  e.target.value = '';
}
function processSheet(file) {
  state.sheetFile = file;
  const size = file.size < 1024 ? `${file.size} B`
             : file.size < 1048576 ? `${(file.size/1024).toFixed(1)} KB`
             : `${(file.size/1048576).toFixed(1)} MB`;
  document.getElementById('sheetDropInner').style.display  = 'none';
  document.getElementById('sheetUploaded').style.display   = 'flex';
  document.getElementById('sheetFileName').textContent     = file.name;
  document.getElementById('sheetFileMeta').textContent     = size;
  document.getElementById('sheetStatus').textContent       = '✓ Uploaded';
  document.getElementById('sheetStatus').style.color       = 'var(--green)';
  showToast(`"${file.name}" uploaded`, 'success');
}
function removeSheet() {
  state.sheetFile = null;
  document.getElementById('sheetDropInner').style.display  = 'flex';
  document.getElementById('sheetUploaded').style.display   = 'none';
  document.getElementById('sheetStatus').textContent       = 'Not uploaded';
  document.getElementById('sheetStatus').style.color       = '';
}

// --- Voice recorder ---
function initWaveformBars() {
  const container = document.getElementById('waveformBars');
  container.innerHTML = '';
  for (let i = 0; i < 40; i++) {
    const bar = document.createElement('div');
    bar.className = 'waveform-bar';
    bar.style.height = '4px';
    container.appendChild(bar);
  }
}

async function toggleRecording() {
  if (state.isRecording) {
    stopRecording();
  } else {
    await startRecording();
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.mediaRecorder  = new MediaRecorder(stream);
    state.recordingChunks = [];
    state.recordingSeconds = 0;
    state.isRecording    = true;

    state.mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) state.recordingChunks.push(e.data);
    };
    state.mediaRecorder.onstop = () => {
      const blob = new Blob(state.recordingChunks, { type: 'audio/webm' });
      state.voiceBlob = blob;
      state.voiceDuration = state.recordingSeconds;

      const url = URL.createObjectURL(blob);
      document.getElementById('voiceAudio').src = url;
      document.getElementById('voicePlayBtn').style.display   = 'flex';
      document.getElementById('voiceDeleteBtn').style.display = 'flex';
      document.getElementById('voiceStatus').textContent = formatTime(state.recordingSeconds) + ' recorded';
      document.getElementById('voiceIdlePrompt').style.display = 'none';

      // Stop all tracks
      stream.getTracks().forEach(t => t.stop());
      showToast('Voice note saved!', 'success');
    };

    state.mediaRecorder.start(100);

    // Timer
    document.getElementById('voiceIdlePrompt').style.display = 'none';
    const btn = document.getElementById('recordBtn');
    btn.classList.add('recording');
    document.getElementById('recordBtnLabel').textContent = 'Stop recording';

    state.recordingInterval = setInterval(() => {
      state.recordingSeconds++;
      document.getElementById('voiceTimer').textContent = formatTime(state.recordingSeconds);
      animateWaveformBars();
    }, 1000);

    // Start bar animation immediately
    initWaveformBars();
    animateWaveformBars();
  } catch (err) {
    showToast('Microphone access denied. Please allow mic in browser settings.', 'error');
    state.isRecording = false;
  }
}

function stopRecording() {
  if (!state.mediaRecorder) return;
  state.isRecording = false;
  clearInterval(state.recordingInterval);
  state.mediaRecorder.stop();

  const btn = document.getElementById('recordBtn');
  btn.classList.remove('recording');
  document.getElementById('recordBtnLabel').textContent = 'Re-record';
}

function animateWaveformBars() {
  const bars = document.querySelectorAll('.waveform-bar');
  bars.forEach(bar => {
    const h = state.isRecording
      ? Math.max(4, Math.random() * 52 + 8)
      : 4;
    bar.style.height = h + 'px';
  });
}

function playVoiceNote() {
  const audio = document.getElementById('voiceAudio');
  if (audio.paused) {
    audio.play();
    document.getElementById('voicePlayBtn').innerHTML =
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>';
    audio.onended = () => {
      document.getElementById('voicePlayBtn').innerHTML =
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>';
    };
  } else {
    audio.pause();
    document.getElementById('voicePlayBtn').innerHTML =
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>';
  }
}

function deleteVoiceNote() {
  if (state.mediaRecorder && state.isRecording) stopRecording();
  state.voiceBlob = null;
  state.voiceDuration = 0;
  document.getElementById('voiceAudio').src = '';
  document.getElementById('voicePlayBtn').style.display   = 'none';
  document.getElementById('voiceDeleteBtn').style.display = 'none';
  document.getElementById('voiceTimer').textContent        = '0:00';
  document.getElementById('voiceStatus').textContent       = 'Not recorded';
  document.getElementById('recordBtnLabel').textContent    = 'Start recording';
  document.getElementById('voiceIdlePrompt').style.display = 'flex';
  initWaveformBars();
  showToast('Voice note deleted', 'info');
}

function formatTime(s) {
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, '0')}`;
}

// --- Preferences text ---
function updateWordCount() {
  const text  = document.getElementById('prefsText').value;
  const words = text.trim() === '' ? 0 : text.trim().split(/\s+/).length;
  const chars = text.length;
  document.getElementById('prefsWordCount').textContent = `${words} word${words !== 1 ? 's' : ''}`;
  document.getElementById('charCount').textContent = `${chars} / 2000`;
  state.prefsText = text;
}
function insertSuggestion(prefix) {
  const ta = document.getElementById('prefsText');
  const val = ta.value;
  ta.value = val + (val && !val.endsWith('\n') ? '\n' : '') + prefix;
  ta.focus();
  updateWordCount();
}

// ── PAGE 5: SUCCESS ─────────────────────────────────────
async function confirmAndFinish() {
  const hasShopify = state.connectedPlatforms.shopify && state.shopifyDomain;
  if (!hasShopify && !state.sheetFile) {
    showToast('Connect Shopify or upload a spreadsheet first — we need some sales history', 'error');
    return;
  }

  const btn = document.getElementById('finishBtn') || document.querySelector('#page-enrich .btn-primary');
  if (btn) { btn.disabled = true; btn.textContent = 'Building your profile…'; }

  // The real onboarding call: every source the user gave us, in one request
  const form = new FormData();
  if (hasShopify)      form.append('shopify_shop', state.shopifyDomain);
  if (state.sheetFile) form.append('file', state.sheetFile);
  const descParts = [];
  if (state.user.businessName) descParts.push(`Shop name: ${state.user.businessName}.`);
  if (state.user.sellerType)   descParts.push(`Sells: ${state.user.sellerType}.`);
  if (state.prefsText.trim())  descParts.push(state.prefsText.trim());
  if (descParts.length) form.append('description', descParts.join(' '));

  let onboard;
  try {
    const res = await fetch(`${API_BASE}/onboard`, { method: 'POST', body: form });
    if (!res.ok) throw new Error((await res.json()).detail || `HTTP ${res.status}`);
    onboard = await res.json();
  } catch (err) {
    showToast('Onboarding failed: ' + err.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Complete profile'; }
    return;
  }
  state.sellerId = onboard.seller_id;
  state.profile  = onboard.profile;

  renderProfileSummary(onboard.profile);
  renderContributions();
  goToPage(4);
  showToast('Profile built — matching Fleek inventory to your shop', 'success');
  loadRecommendations();
}

function renderContributions() {
  // Build contributions list
  const contributions = [];
  if (state.importedData.orders > 0)
    contributions.push({ icon: '📦', label: `${state.importedData.orders} orders imported` });
  if (state.images.length > 0)
    contributions.push({ icon: '📸', label: `${state.images.length} image${state.images.length > 1 ? 's' : ''}` });
  if (state.voiceBlob)
    contributions.push({ icon: '🎙️', label: `Voice note (${formatTime(state.voiceDuration)})` });
  if (state.sheetFile)
    contributions.push({ icon: '📊', label: state.sheetFile.name });
  if (state.prefsText.trim().length > 0) {
    const wc = state.prefsText.trim().split(/\s+/).length;
    contributions.push({ icon: '✍️', label: `${wc} word preference note` });
  }

  document.getElementById('successContributions').innerHTML =
    contributions.map(c => `
      <div class="contribution-chip">
        <span>${c.icon}</span>
        <span>${c.label}</span>
      </div>
    `).join('');
}

function renderProfileSummary(profile) {
  const el = document.getElementById('profileSummary');
  if (!el) return;
  const band = profile.price_band;
  const chips = [
    ...profile.aesthetic.map(a => `<div class="profile-chip chip-aesthetic">${a}</div>`),
    `<div class="profile-chip chip-band">£${Math.round(band.min)}–£${Math.round(band.max)} · median £${Math.round(band.median)}</div>`,
    ...profile.saturation.gaps.map(g => `<div class="profile-chip chip-gap">Gap: ${g}</div>`),
    ...profile.saturation.oversupplied.map(o => `<div class="profile-chip chip-over">Well stocked: ${o}</div>`),
  ];
  el.innerHTML = `<h3 class="recs-heading">Your shop's DNA</h3><div class="profile-chips">${chips.join('')}</div>`;
}

async function loadRecommendations() {
  const el = document.getElementById('recsSection');
  if (!el || !state.sellerId) return;
  el.innerHTML = `<h3 class="recs-heading">Sourcing picks for you</h3>
    <div class="recs-loading"><div class="spinner"></div><span>Matching Fleek inventory to your profile…</span></div>`;

  let data;
  try {
    const res = await fetch(`${API_BASE}/recommendations?seller_id=${encodeURIComponent(state.sellerId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    data = await res.json();
  } catch (err) {
    el.innerHTML = `<h3 class="recs-heading">Sourcing picks for you</h3>
      <p class="recs-empty">Couldn't load recommendations (${err.message}) — try again from the dashboard.</p>`;
    return;
  }

  const note = (data.relaxations || []).length
    ? `<p class="recs-note">To find enough stock we ${data.relaxations.join(' and ')}.</p>` : '';

  el.innerHTML = `<h3 class="recs-heading">Sourcing picks for you</h3>${note}
    <div class="bundle-list">${data.bundles.map(renderBundle).join('')}</div>`;
}

function renderBundle(b) {
  const imgs = b.items.slice(0, 4).map(i =>
    `<img src="${i.image_url}" alt="${i.title}" title="${i.title} — £${i.fleek_cost}" loading="lazy" />`).join('');
  const cats = [...new Set(b.items.map(i => i.category))].join(' · ');
  return `
    <div class="bundle-card">
      <div class="bundle-images">${imgs}</div>
      <div class="bundle-body">
        <div class="bundle-title">${b.items.length} pieces · ${cats}</div>
        <div class="bundle-stats">
          <span>£${b.total_cost} bundle cost</span>
          <span>${b.est_margin}× est. margin</span>
          <span>~${b.est_clear_days} days to clear</span>
        </div>
        <p class="bundle-rationale">${b.rationale}</p>
        <button class="btn-secondary bundle-btn" onclick="showToast('Bundle from supplier ${b.supplier_id} added to your Fleek cart','success')">Add bundle to cart</button>
      </div>
    </div>`;
}

// ── HELP MODAL ─────────────────────────────────────────
document.getElementById('helpBtn').addEventListener('click', () =>
  document.getElementById('helpModal').classList.add('open'));
function closeHelp() {
  document.getElementById('helpModal').classList.remove('open');
}
document.getElementById('helpModal').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeHelp();
});

// ── TOAST ──────────────────────────────────────────────
let toastTimer;
function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast ${type} show`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 3400);
}

// ── UTILS ──────────────────────────────────────────────
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function simulateOAuth() { return sleep(1400); }

async function fetchWithFallback(url, options, fallback) {
  try {
    const res = await Promise.race([
      fetch(url, options),
      new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 4000)),
    ]);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    console.warn('[FleekCompanion] API unavailable – using mock data');
    return fallback;
  }
}

// ── MOCK DATA ──────────────────────────────────────────
function generateMockData() {
  const now = new Date();
  const ago = n => new Date(now - n * 86400000).toISOString();
  const result = {};

  if (state.connectedPlatforms.ebay) {
    result.ebay = {
      profile: { platform:'ebay', seller_id:'ebay_user', username:'fashion_seller_uk', rating:98.5, total_items_sold:312 },
      items: [
        { platform:'ebay', item_id:'e001', title:'Zara Floral Midi Dress – Size M', price:24.99, currency:'GBP', brand:'Zara', condition:'Very Good', size:'M', status:'active' },
        { platform:'ebay', item_id:'e002', title:'ASOS Wide Leg Linen Trousers', price:18.50, currency:'GBP', brand:'ASOS', condition:'Good', size:'12', status:'active' },
        { platform:'ebay', item_id:'e003', title:'Nike Air Force 1 White UK7', price:55.00, currency:'GBP', brand:'Nike', condition:'Very Good', size:'UK7', status:'sold' },
      ],
      orders: [
        { platform:'ebay', order_id:'ORD-8821', item_id:'e003', title:'Nike Air Force 1 White UK7', price:55.00, currency:'GBP', buyer_username:'buyer_sarah92', sold_at:ago(2), status:'shipped', tracking_number:'1Z999AA10123456784' },
        { platform:'ebay', order_id:'ORD-8756', item_id:'e001', title:'Zara Floral Midi Dress', price:24.99, currency:'GBP', buyer_username:'emma_k', sold_at:ago(5), status:'delivered' },
        { platform:'ebay', order_id:'ORD-8701', item_id:'e004', title:'H&M Oversized Blazer Black', price:32.00, currency:'GBP', buyer_username:'style_hunter', sold_at:ago(9), status:'delivered' },
        { platform:'ebay', order_id:'ORD-8640', item_id:'e005', title:'Topshop Ribbed Knit Sweater', price:14.99, currency:'GBP', buyer_username:'nora_fashion', sold_at:ago(14), status:'pending' },
      ],
      total_items_fetched: 3, total_orders_fetched: 4,
    };
  }

  if (state.connectedPlatforms.shopify) {
    result.shopify = {
      profile: { platform:'shopify', seller_id: state.shopifyDomain || 'demo.myshopify.com', username:'demo-store', rating:null },
      items: [
        { platform:'shopify', item_id:'s001', title:"Vintage Levi's 501 Jeans W28 L30", price:65.00, currency:'GBP', brand:"Levi's", condition:'Good', size:'W28 L30', status:'active' },
        { platform:'shopify', item_id:'s002', title:'Stone Island Patch Logo Hoodie', price:120.00, currency:'GBP', brand:'Stone Island', condition:'Very Good', size:'L', status:'active' },
        { platform:'shopify', item_id:'s003', title:'Adidas Samba OG White Green', price:78.00, currency:'GBP', brand:'Adidas', condition:'New', size:'UK8', status:'active' },
      ],
      orders: [
        { platform:'shopify', order_id:'SHP-1042', item_id:'s001', title:"Vintage Levi's 501 Jeans", price:65.00, currency:'GBP', buyer_username:'james_t', sold_at:ago(1), status:'fulfilled', tracking_number:'RM123456789GB' },
        { platform:'shopify', order_id:'SHP-1038', item_id:'s003', title:'Adidas Samba OG White Green', price:78.00, currency:'GBP', buyer_username:'alex_b', sold_at:ago(4), status:'shipped', tracking_number:'RM987654321GB' },
        { platform:'shopify', order_id:'SHP-1021', item_id:'s002', title:'Stone Island Patch Logo Hoodie', price:120.00, currency:'GBP', buyer_username:'streetwear_fan', sold_at:ago(7), status:'delivered' },
      ],
      total_items_fetched: 3, total_orders_fetched: 3,
    };
  }

  if (state.connectedPlatforms.vinted) {
    result.vinted = {
      profile: { platform:'vinted', seller_id: state.vintedSellerId || '99999', username:`vinted_user_${state.vintedSellerId}`, rating:4.9 },
      items: [
        { platform:'vinted', item_id:'v001', title:'M&S Pure Linen Shirt White 10', price:12.00, currency:'GBP', brand:'M&S', condition:'Good', size:'10', status:'active' },
        { platform:'vinted', item_id:'v002', title:'Cos Wool Blend Coat Camel XS', price:85.00, currency:'GBP', brand:'COS', condition:'Very Good', size:'XS', status:'active' },
      ],
      orders: [],
      total_items_fetched: 2, total_orders_fetched: 0,
    };
  }

  return result;
}

// ── INIT ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initWaveformBars();
  // Animate hero orbs
  document.querySelectorAll('.hero-orb').forEach(o => {
    o.style.opacity = '0';
    setTimeout(() => { o.style.transition = 'opacity 1s ease'; o.style.opacity = '0.35'; }, 100);
  });
});
