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
  // marketplace page gets the real Fleek navbar, onboarding keeps the stepper
  const isHome = PAGES[index] === 'page-success';
  document.getElementById('onboardNav').style.display = isHome ? 'none' : 'flex';
  document.getElementById('marketNav').style.display  = isHome ? 'flex' : 'none';
  if (isHome) {
    const initials = ((state.user.firstName[0] || 'F') + (state.user.lastName[0] || 'L')).toUpperCase();
    document.getElementById('navAvatar').textContent = initials;
  }
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
  updateImportButton();
  showToast(`${platform.charAt(0).toUpperCase() + platform.slice(1)} disconnected`, 'info');
}

function updateImportButton() {
  const any = Object.values(state.connectedPlatforms).some(Boolean) || !!state.sheetFile;
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
  state.importedData = { orders: totalOrders, items: totalItems, platforms: connectedList };

  fill.style.width = '100%';
  label.textContent = `Import complete — ${totalOrders} orders, ${totalItems} listings`;
  sub.textContent = '';
  await sleep(600);
  progress.style.display = 'none';

  // Update enrich page chip
  const sources = connectedList.map(p => p.charAt(0).toUpperCase() + p.slice(1));
  if (state.sheetFile) sources.push('your spreadsheet');
  document.getElementById('importSummaryText').textContent =
    `${totalOrders} orders & ${totalItems} listings from ${sources.join(' + ') || 'your data'}` +
    (state.sheetFile ? ' (spreadsheet merges at the final step)' : '');

  showToast(connectedList.length ? `✓ Imported ${totalOrders} orders` : '✓ Spreadsheet ready — it merges when you complete your profile', 'success');
  goToPage(3); // enrich page
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
  updateImportButton();
  showToast(`"${file.name}" uploaded`, 'success');
}
function removeSheet() {
  state.sheetFile = null;
  document.getElementById('sheetDropInner').style.display  = 'flex';
  document.getElementById('sheetUploaded').style.display   = 'none';
  document.getElementById('sheetStatus').textContent       = 'Not uploaded';
  document.getElementById('sheetStatus').style.color       = '';
  updateImportButton();
}

// --- Voice recorder ---
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
      
      // Stop all tracks
      stream.getTracks().forEach(t => t.stop());
      showToast('Voice note saved!', 'success');
    };

    state.mediaRecorder.start(100);

    // Timer
    const btn = document.getElementById('recordBtn');
    btn.classList.add('recording');
    document.getElementById('recordBtnLabel').textContent = 'Stop recording';

    state.recordingInterval = setInterval(() => {
      state.recordingSeconds++;
      document.getElementById('voiceTimer').textContent = formatTime(state.recordingSeconds);
    }, 1000);

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
  document.getElementById('recordBtnLabel').textContent    = 'Start recording';
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
  if (state.voiceBlob) form.append('voice', state.voiceBlob, 'voice-note.webm');
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
  loadMarketplace();
}

function renderContributions() {
  // Build contributions list
  const contributions = [];
  if (state.importedData.orders > 0)
    contributions.push({ icon: '📦', label: `${state.importedData.orders} orders imported` });
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
        <div class="ai-reason">
          <div class="ai-reason-label"><span class="ai-star">✦</span> Why Fleek picked this for you</div>
          <p>${b.rationale}</p>
        </div>
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



// ── PROFILE PAGE (avatar click) ────────────────────────
async function openProfile() {
  if (!state.sellerId) { showToast('Complete onboarding first', 'error'); return; }
  const overlay = document.getElementById('profileOverlay');
  overlay.style.display = 'flex';
  const el = document.getElementById('profileContent');
  el.innerHTML = '<div class="recs-loading"><div class="spinner"></div><span>Writing your profile…</span></div>';

  let data;
  try {
    const res = await fetch(`${API_BASE}/seller/${encodeURIComponent(state.sellerId)}/story`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    data = await res.json();
  } catch (err) {
    el.innerHTML = `<p class="recs-empty">Could not load profile (${err.message}).</p>`;
    return;
  }
  el.innerHTML = renderProfilePage(data.profile, data.story);
}

function closeProfile() {
  document.getElementById('profileOverlay').style.display = 'none';
}

function renderProfilePage(p, s) {
  const u = state.user;
  const initials = ((u.firstName[0] || 'F') + (u.lastName[0] || 'L')).toUpperCase();
  const band = p.price_band;
  const st = p.stats;

  const statTiles = st ? `
    <div class="pr-stats">
      <div class="pr-stat"><span class="pr-stat-v">£${Number(st.est_monthly_revenue).toLocaleString()}</span><span class="pr-stat-l">est. monthly revenue</span></div>
      <div class="pr-stat"><span class="pr-stat-v">${st.items_per_week}</span><span class="pr-stat-l">pieces sold / week</span></div>
      <div class="pr-stat"><span class="pr-stat-v">£${st.avg_item_price.toFixed(0)}</span><span class="pr-stat-l">avg. sale price</span></div>
      <div class="pr-stat"><span class="pr-stat-v">${st.orders_analysed}</span><span class="pr-stat-l">sales analysed</span></div>
      ${st.active_listings ? `<div class="pr-stat"><span class="pr-stat-v">${st.active_listings}</span><span class="pr-stat-l">active listings</span></div>` : ''}
      <div class="pr-stat"><span class="pr-stat-v">£${Number(p.budget).toFixed(0)}</span><span class="pr-stat-l">restock budget</span></div>
    </div>` : '';

  const bandPct = band.max > band.min ? ((band.median - band.min) / (band.max - band.min)) * 100 : 50;

  return `
    <div class="pr-header">
      <div class="pr-avatar">${initials}</div>
      <div class="pr-id">
        <h2>${u.businessName || 'Your shop'}</h2>
        <p>${u.firstName} ${u.lastName}${u.email ? ' · ' + u.email : ''}${state.shopifyDomain ? ' · ' + state.shopifyDomain : ''}</p>
        <p class="pr-headline">"${s.headline}"</p>
      </div>
    </div>

    ${statTiles}
    <p class="pr-size">${s.size_estimate || ''}</p>

    <div class="pr-grid">
      <div class="pr-card"><h4>About this shop</h4><p>${s.about}</p></div>
      <div class="pr-card"><h4>Who buys from you</h4><p>${s.buyer_persona}</p></div>
      <div class="pr-card"><h4>What's working</h4><ul>${s.strengths.map(x => `<li>${x}</li>`).join('')}</ul></div>
      <div class="pr-card"><h4>Where to grow</h4><ul>${s.opportunities.map(x => `<li>${x}</li>`).join('')}</ul></div>
      <div class="pr-card pr-card-wide"><h4>Sourcing strategy</h4><p>${s.strategy}</p></div>
    </div>

    <div class="pr-bonnet">
      <h4>Under the bonnet <span class="pr-bonnet-sub">— the machine profile driving your recommendations</span></h4>
      <div class="pr-tags">
        ${p.aesthetic.map(a => `<span class="profile-chip chip-aesthetic">${a}</span>`).join('')}
        ${p.saturation.gaps.map(g => `<span class="profile-chip chip-gap">gap: ${g}</span>`).join('')}
        ${p.saturation.oversupplied.map(o => `<span class="profile-chip chip-over">saturated: ${o}</span>`).join('')}
        <span class="profile-chip chip-band">target margin ≥${p.assumed_margin_multiple}×</span>
      </div>
      <div class="pr-band">
        <div class="pr-band-track"><div class="pr-band-marker" style="left:${bandPct}%"></div></div>
        <div class="pr-band-labels"><span>£${band.min.toFixed(0)}</span><span>median £${band.median.toFixed(0)}</span><span>£${band.max.toFixed(0)}</span></div>
      </div>
      <details class="pr-json">
        <summary>Raw profile JSON (what the vector search and economics filter consume)</summary>
        <pre>${JSON.stringify(p, null, 2)}</pre>
      </details>
    </div>`;
}

// ── MARKETPLACE HOME ───────────────────────────────────
const market = { offset: 0, limit: 24, total: 0, category: null, q: null };

function loadMarketplace() {
  loadCollections();
  loadProducts();
}

async function loadCollections() {
  const row = document.getElementById('collectionRow');
  if (!row) return;
  try {
    const data = await (await fetch(`${API_BASE}/inventory/categories`)).json();
    row.innerHTML = data.categories.map(c => `
      <div class="collection-tile" onclick="filterMarketCategory('${c.category}')"
           style="background-image:url('${c.image_url}')">
        <span>${c.category}</span>
      </div>`).join('');
  } catch { row.innerHTML = ''; }
}

function filterMarketCategory(cat) {
  market.category = cat; market.q = null; market.offset = 0;
  document.getElementById('navSearch').value = '';
  loadProducts();
}

function searchMarket() {
  const q = document.getElementById('navSearch').value.trim();
  market.q = q || null; market.category = null; market.offset = 0;
  loadProducts();
  document.getElementById('productGrid')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function clearMarketFilter() {
  market.category = null; market.q = null; market.offset = 0;
  document.getElementById('navSearch').value = '';
  loadProducts();
}

async function loadProducts(append = false) {
  const grid = document.getElementById('productGrid');
  if (!grid) return;
  const params = new URLSearchParams({ limit: market.limit, offset: market.offset });
  if (market.category) params.set('category', market.category);
  if (market.q) params.set('q', market.q);

  let data;
  try {
    data = await (await fetch(`${API_BASE}/inventory?${params}`)).json();
  } catch { grid.innerHTML = '<p class="recs-empty">Could not load inventory.</p>'; return; }

  market.total = data.total;
  const cards = data.items.map(productCard).join('');
  if (append) grid.insertAdjacentHTML('beforeend', cards);
  else grid.innerHTML = cards || '<p class="recs-empty">Nothing matches that search.</p>';

  const title = market.category ? market.category
    : market.q ? `Results for "${market.q}"` : 'Latest drops';
  document.getElementById('gridTitle').textContent = title;
  document.getElementById('clearFilterBtn').style.display = (market.category || market.q) ? '' : 'none';
  document.getElementById('loadMoreBtn').style.display =
    market.offset + market.limit < market.total ? '' : 'none';
}

function loadMoreProducts() {
  market.offset += market.limit;
  loadProducts(true);
}

function productCard(i) {
  const discount = Math.round((1 - i.fleek_cost / i.predicted_resale) * 100);
  return `
    <div class="product-card">
      <div class="product-img">
        <img src="${i.image_url}" alt="${i.title}" loading="lazy" />
        ${discount >= 30 ? `<span class="disc-badge">${discount}% Discount</span>` : ''}
      </div>
      <div class="product-body">
        <p class="p-title">${i.title}</p>
        <div class="p-rating"><span class="p-stars">★★★★★</span><span>${i.rating ?? ''}</span></div>
        <div class="p-price-row">
          <span class="p-price">£${i.fleek_cost.toFixed(0)}</span>
          <span class="p-compare">£${i.predicted_resale.toFixed(0)}</span>
        </div>
        <p class="p-perpc">est. resale value</p>
        <span class="ship-chip">Shipping Inc.</span>
      </div>
    </div>`;
}

// ── INIT ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Animate hero orbs
  document.querySelectorAll('.hero-orb').forEach(o => {
    o.style.opacity = '0';
    setTimeout(() => { o.style.transition = 'opacity 1s ease'; o.style.opacity = '0.35'; }, 100);
  });
});
