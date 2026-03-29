const startButton = document.getElementById("start-session");
const startPanel = document.getElementById("session-start");
const scanPanel = document.getElementById("scan-panel");
const statusEl = document.getElementById("status");
const scanResultEl = document.getElementById("scan-result");
const scanHintEl = document.getElementById("scan-hint");
const counterValue = document.getElementById("counter-value");
const presentValue = document.getElementById("present-value");
const linkForm = document.getElementById("link-form");
const linkInput = document.getElementById("link-input");
const linkBtn = document.getElementById("link-btn");
const linkResult = document.getElementById("link-result");
const idleOverlay = document.getElementById("idle-overlay");
const idleCount = document.getElementById("idle-count");

const registerModal = document.getElementById("register-modal");
const regTag = document.getElementById("reg-tag");
const regPnr = document.getElementById("reg-pnr");
const regPhone = document.getElementById("reg-phone");
const regEmail = document.getElementById("reg-email");
const regSubmit = document.getElementById("reg-submit");
const regCancel = document.getElementById("reg-cancel");
const regResult = document.getElementById("register-result");
const regPnrError = document.getElementById("reg-pnr-error");
const regGuestInfo = document.getElementById("register-guest-info");

let lastScan = { value: null, time: 0 };
let pendingCardId = null;
let pendingRegistration = null;
let scanner = null;
let idleTimer = null;

const IDLE_DELAY_MS = 10000;

/* --- Audio feedback via Web Audio API --- */
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function playTone(freq, duration, type = "sine") {
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.type = type;
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(0.18, audioCtx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  osc.start();
  osc.stop(audioCtx.currentTime + duration);
}

function playCheckinSound() {
  playTone(660, 0.12);
  setTimeout(() => playTone(880, 0.18), 100);
}

function playCheckoutSound() {
  playTone(440, 0.12);
  setTimeout(() => playTone(330, 0.18), 100);
}

function playErrorSound() {
  playTone(220, 0.25, "square");
}

/* --- QR reader visual feedback --- */
const qrReader = document.getElementById("qr-reader");

function flashQrBorder(color) {
  if (!qrReader) return;
  qrReader.classList.remove("flash-ok", "flash-out", "flash-warn");
  void qrReader.offsetWidth; // force reflow for re-trigger
  const cls = color === "ok" ? "flash-ok" : color === "warn" ? "flash-warn" : "flash-out";
  qrReader.classList.add(cls);
  setTimeout(() => qrReader.classList.remove(cls), 800);
}

function setStatus(text, level) {
  statusEl.textContent = text;
  statusEl.className = "status";
  if (level) statusEl.classList.add(level);
}

function updateCounters(total, present) {
  if (counterValue && total !== undefined) counterValue.textContent = total;
  if (presentValue && present !== undefined) presentValue.textContent = present;
}

function showLinkForm(cardId) {
  pendingCardId = cardId;
  if (linkForm) linkForm.style.display = "block";
  if (linkInput) { linkInput.value = ""; linkInput.focus(); }
  if (linkResult) linkResult.textContent = "";
}

function hideLinkForm() {
  pendingCardId = null;
  if (linkForm) linkForm.style.display = "none";
}

function streakText(streak) {
  if (!streak || streak < 2) return "";
  return ` \u{1F525} ${streak} tr\u00e4ffar i rad!`;
}

function showIdleScreen() {
  if (!idleOverlay) return;
  const present = presentValue ? presentValue.textContent : "0";
  if (idleCount) idleCount.textContent = present;
  idleOverlay.style.display = "flex";
}

function hideIdleScreen() {
  if (idleOverlay) idleOverlay.style.display = "none";
}

function resetIdleTimer() {
  hideIdleScreen();
  clearTimeout(idleTimer);
  idleTimer = setTimeout(showIdleScreen, IDLE_DELAY_MS);
}

async function fetchAttendance() {
  try {
    const res = await fetch("/api/sessions/attendance");
    const data = await res.json();
    if (data.open) updateCounters(data.total, data.present);
  } catch (err) { /* ignore */ }
}

async function startSession() {
  const res = await fetch("/api/sessions/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ location: "Studiefrämjandet, Kungsgatan 42, 461 34 Trollhättan", notes: "" }),
  });
  if (!res.ok) {
    setStatus("ERROR", "warn");
    scanResultEl.textContent = "Kunde inte starta session.";
    return;
  }
  startPanel.style.display = "none";
  scanPanel.style.display = "block";
  initScanner();
}

async function initScanner() {
  await fetchAttendance();

  scanner = new Html5Qrcode("qr-reader");
  try {
    await scanner.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: { width: 250, height: 250 } },
      onScanSuccess,
      () => {} // ignore scan failures (no QR in frame)
    );
    setStatus("READY", "");
    scanHintEl.textContent = "Skanna ditt medlemskort f\u00f6r att checka in.";
    resetIdleTimer();
  } catch (err) {
    setStatus("KAMERA BLOCKERAD", "warn");
    scanHintEl.textContent = "Till\u00e5t kamera\u00e5tkomst f\u00f6r att scanna QR-koder.";
  }
}

async function onScanSuccess(decodedText) {
  const now = Date.now();
  if (decodedText === lastScan.value && now - lastScan.time < 4000) return;
  lastScan = { value: decodedText, time: now };
  resetIdleTimer();
  await sendCheckin(decodedText);
}

async function sendCheckin(qrData) {
  hideLinkForm();
  setStatus("SCANNAD", "info");
  const res = await fetch("/api/checkin", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ qr_data: qrData }),
  });
  const data = await res.json();
  if (data.status === "ok") {
    setStatus("INCHECKAD", "ok");
    const streak = streakText(data.streak);
    scanResultEl.textContent = `V\u00e4lkommen ${data.member_name}! Du \u00e4r #${data.checkin_number} idag${streak}`;
    updateCounters(data.checkin_number, data.present);
    playCheckinSound();
    flashQrBorder("ok");
  } else if (data.status === "checkout") {
    setStatus("UTCHECKAD", "info");
    scanResultEl.textContent = `Hej d\u00e5 ${data.member_name}! Vi ses n\u00e4sta g\u00e5ng \u{1F44B}`;
    updateCounters(undefined, data.present);
    playCheckoutSound();
    flashQrBorder("out");
  } else if (data.status === "already_left") {
    setStatus("REDAN UTCHECKAD", "warn");
    scanResultEl.textContent = `${data.member_name} har redan checkat ut`;
    playErrorSound();
    flashQrBorder("warn");
  } else if (data.status === "unknown") {
    setStatus("OK\u00c4ND", "warn");
    scanResultEl.textContent = "QR-koden k\u00e4nns inte igen.";
    showLinkForm(data.card_id);
    playErrorSound();
    flashQrBorder("warn");
  } else if (data.status === "no_session") {
    setStatus("INGEN SESSION", "warn");
    scanResultEl.textContent = "Ingen aktiv session.";
    playErrorSound();
  } else {
    setStatus("FEL", "warn");
    scanResultEl.textContent = "Scanningsfel.";
  }
  resetIdleTimer();
}

async function linkAndCheckin() {
  if (!pendingCardId || !linkInput) return;
  const value = linkInput.value.trim();
  if (!value) return;

  const body = { card_id: pendingCardId, player_name: value };

  const res = await fetch("/api/link-and-checkin", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.status === "ok") {
    setStatus("INCHECKAD", "ok");
    const streak = streakText(data.streak);
    scanResultEl.textContent = `V\u00e4lkommen ${data.member_name}! Du \u00e4r #${data.checkin_number} idag${streak}`;
    updateCounters(data.checkin_number, data.present);
    hideLinkForm();
  } else if (data.status === "already_in") {
    setStatus("REDAN INCHECKAD", "info");
    scanResultEl.textContent = `${data.member_name} \u2014 QR kopplad, redan incheckad`;
    hideLinkForm();
  } else if (data.status === "not_found") {
    if (linkResult) linkResult.textContent = "Spelare hittades inte. F\u00f6rs\u00f6k igen.";
  } else {
    if (linkResult) linkResult.textContent = data.message || "N\u00e5got gick fel.";
  }
  resetIdleTimer();
}

// === Personnummer Luhn validation (mirrors src/validation.py) ===

function sanitizePersonnummer(value) {
  return value.replace(/[-\s]/g, "").replace(/\D/g, "");
}

function validatePersonnummer(value) {
  const digits = sanitizePersonnummer(value);
  if (digits.length !== 10 && digits.length !== 12) {
    return { valid: false, error: "Måste vara 10 eller 12 siffror" };
  }
  const d = digits.slice(-10);
  const month = parseInt(d.slice(2, 4), 10);
  const day = parseInt(d.slice(4, 6), 10);
  if (month < 1 || month > 12) return { valid: false, error: "Ogiltig månad" };
  if (day < 1 || day > 31) return { valid: false, error: "Ogiltig dag" };

  const weights = [2, 1, 2, 1, 2, 1, 2, 1, 2, 1];
  let total = 0;
  for (let i = 0; i < 10; i++) {
    let val = parseInt(d[i], 10) * weights[i];
    if (val >= 10) val -= 9;
    total += val;
  }
  if (total % 10 !== 0) return { valid: false, error: "Ogiltig checksumma" };
  return { valid: true, error: "" };
}

// === Guest registration modal ===

function validateRegisterForm() {
  const tag = regTag ? regTag.value.trim() : "";
  const pnr = regPnr ? regPnr.value.trim() : "";
  const pnrResult = pnr ? validatePersonnummer(pnr) : { valid: false, error: "" };

  if (regPnrError) {
    regPnrError.textContent = pnr && !pnrResult.valid ? pnrResult.error : "";
  }
  if (regSubmit) {
    regSubmit.disabled = !(tag.length > 0 && pnrResult.valid);
  }
}

function showRegisterForm(checkinId, guestName) {
  pendingRegistration = { checkinId, guestName };
  if (regGuestInfo) regGuestInfo.textContent = `Registrera ${guestName} som medlem i FGC Trollhättan`;
  if (regTag) regTag.value = "";
  if (regPnr) regPnr.value = "";
  if (regPhone) regPhone.value = "";
  if (regEmail) regEmail.value = "";
  if (regResult) { regResult.textContent = ""; regResult.className = "register-result"; }
  if (regPnrError) regPnrError.textContent = "";
  if (regSubmit) regSubmit.disabled = true;
  if (registerModal) registerModal.style.display = "flex";
  if (regTag) regTag.focus();
  resetIdleTimer();
}

function hideRegisterForm() {
  pendingRegistration = null;
  if (registerModal) registerModal.style.display = "none";
}

async function submitRegistration() {
  if (!pendingRegistration) return;
  const tag = regTag ? regTag.value.trim() : "";
  const personnummer = regPnr ? sanitizePersonnummer(regPnr.value) : "";
  const telephone = regPhone ? regPhone.value.trim() : "";
  const email = regEmail ? regEmail.value.trim() : "";

  if (!tag || !personnummer) return;

  if (regSubmit) regSubmit.disabled = true;
  if (regResult) { regResult.textContent = "Registrerar..."; regResult.className = "register-result"; }

  try {
    const res = await fetch("/api/guest/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        checkin_id: pendingRegistration.checkinId,
        tag,
        personnummer,
        telephone,
        email,
      }),
    });
    const data = await res.json();
    if (data.success) {
      if (regResult) {
        regResult.textContent = `Välkommen som medlem, ${tag}!`;
        regResult.className = "register-result success";
      }
      setTimeout(() => {
        hideRegisterForm();
        fetchAttendance();
      }, 2000);
    } else {
      if (regResult) {
        regResult.textContent = data.message || "Registreringen misslyckades";
        regResult.className = "register-result error";
      }
      if (regSubmit) regSubmit.disabled = false;
    }
  } catch (err) {
    if (regResult) {
      regResult.textContent = "Nätverksfel — försök igen";
      regResult.className = "register-result error";
    }
    if (regSubmit) regSubmit.disabled = false;
  }
  resetIdleTimer();
}

// === Guest checkin (no QR needed) ===

const guestCheckinToggle = document.getElementById("guest-checkin-toggle");
const guestCheckinForm = document.getElementById("guest-checkin-form");
const guestNameInput = document.getElementById("guest-name-input");
const guestCheckinBtn = document.getElementById("guest-checkin-btn");
const guestCheckinResult = document.getElementById("guest-checkin-result");

function toggleGuestCheckin() {
  if (!guestCheckinForm) return;
  const visible = guestCheckinForm.style.display !== "none";
  if (visible && guestNameInput && guestNameInput.value.trim()) {
    submitGuestCheckin();
    return;
  }
  guestCheckinForm.style.display = visible ? "none" : "block";
  if (!visible && guestNameInput) { guestNameInput.value = ""; guestNameInput.focus(); }
  if (guestCheckinResult) { guestCheckinResult.textContent = ""; guestCheckinResult.className = "guest-checkin-result"; }
  resetIdleTimer();
}

async function submitGuestCheckin() {
  const name = guestNameInput ? guestNameInput.value.trim() : "";
  if (!name) return;

  try {
    const res = await fetch("/api/guest/checkin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ guest_name: name }),
    });
    const data = await res.json();
    if (data.status === "ok") {
      setStatus("INCHECKAD", "ok");
      scanResultEl.textContent = `Välkommen ${data.guest_name}! Du är #${data.checkin_number} idag`;
      updateCounters(data.checkin_number, data.present);
      if (guestCheckinForm) guestCheckinForm.style.display = "none";
      if (guestCheckinResult) { guestCheckinResult.textContent = ""; guestCheckinResult.className = "guest-checkin-result"; }
      if (guestNameInput) guestNameInput.value = "";
    } else if (data.status === "no_session") {
      if (guestCheckinResult) { guestCheckinResult.textContent = "Ingen aktiv session."; guestCheckinResult.className = "guest-checkin-result error"; }
    } else {
      if (guestCheckinResult) { guestCheckinResult.textContent = data.error || "Något gick fel"; guestCheckinResult.className = "guest-checkin-result error"; }
    }
  } catch (err) {
    if (guestCheckinResult) { guestCheckinResult.textContent = "Nätverksfel — försök igen"; guestCheckinResult.className = "guest-checkin-result error"; }
  }
  resetIdleTimer();
}

// === Kiosk guest search → register ===

const kioskRegBtn = document.getElementById("kiosk-register-btn");
const guestSearchForm = document.getElementById("guest-search-form");
const guestSearchInput = document.getElementById("guest-search-input");
const guestSearchBtn = document.getElementById("guest-search-btn");
const guestSearchResult = document.getElementById("guest-search-result");

function toggleGuestSearch() {
  if (!guestSearchForm) return;
  const visible = guestSearchForm.style.display !== "none";
  guestSearchForm.style.display = visible ? "none" : "block";
  if (!visible && guestSearchInput) { guestSearchInput.value = ""; guestSearchInput.focus(); }
  if (guestSearchResult) guestSearchResult.innerHTML = "";
  resetIdleTimer();
}

async function searchGuestCheckins() {
  const query = guestSearchInput ? guestSearchInput.value.trim().toLowerCase() : "";
  if (!query || !guestSearchResult) return;

  try {
    const res = await fetch("/api/sessions/attendance");
    const data = await res.json();
    if (!data.open) {
      guestSearchResult.textContent = "Ingen aktiv session.";
      return;
    }
    const guests = data.checkins.filter(c => c.is_guest && !c.checked_out && c.name.toLowerCase().includes(query));
    if (guests.length === 0) {
      guestSearchResult.textContent = "Ingen gäst med det namnet hittades.";
      return;
    }
    const ul = document.createElement("ul");
    ul.className = "guest-match-list";
    for (const g of guests) {
      const li = document.createElement("li");
      li.textContent = g.name;
      const btn = document.createElement("button");
      btn.className = "btn-register";
      btn.textContent = "Välj";
      btn.addEventListener("click", () => {
        guestSearchForm.style.display = "none";
        guestSearchResult.innerHTML = "";
        showRegisterForm(g.checkin_id, g.name);
      });
      li.appendChild(btn);
      ul.appendChild(li);
    }
    guestSearchResult.innerHTML = "";
    guestSearchResult.appendChild(ul);
  } catch (err) {
    guestSearchResult.textContent = "Kunde inte söka — försök igen.";
  }
  resetIdleTimer();
}

// === Member name checkin ===

const memberSearchInput = document.getElementById("member-search-input");
const memberSearchResults = document.getElementById("member-search-results");
const memberCheckinResult = document.getElementById("member-checkin-result");
let memberSearchTimeout = null;

async function searchMembers() {
  const q = memberSearchInput ? memberSearchInput.value.trim() : "";
  if (q.length < 2) {
    if (memberSearchResults) memberSearchResults.style.display = "none";
    return;
  }
  try {
    const res = await fetch(`/api/players/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (!data.results || data.results.length === 0) {
      if (memberSearchResults) {
        memberSearchResults.style.display = "none";
      }
      if (memberCheckinResult) {
        memberCheckinResult.textContent = "Ingen spelare hittad.";
        memberCheckinResult.className = "guest-checkin-result error";
      }
      return;
    }
    if (memberCheckinResult) { memberCheckinResult.textContent = ""; memberCheckinResult.className = "guest-checkin-result"; }
    if (memberSearchResults) {
      memberSearchResults.innerHTML = "";
      for (const p of data.results) {
        const li = document.createElement("li");
        const nameSpan = document.createElement("span");
        nameSpan.textContent = p.name + (p.tag ? ` (${p.tag})` : "");
        li.appendChild(nameSpan);
        const btn = document.createElement("button");
        btn.className = "btn primary btn-sm";
        btn.textContent = "Checka in";
        btn.addEventListener("click", () => checkinMemberByUuid(p.uuid, p.name));
        li.appendChild(btn);
        memberSearchResults.appendChild(li);
      }
      memberSearchResults.style.display = "block";
    }
  } catch (err) {
    if (memberCheckinResult) { memberCheckinResult.textContent = "Sökfel — försök igen."; memberCheckinResult.className = "guest-checkin-result error"; }
  }
  resetIdleTimer();
}

async function checkinMemberByUuid(uuid, name) {
  if (memberSearchResults) memberSearchResults.style.display = "none";
  if (memberSearchInput) memberSearchInput.value = "";
  try {
    const res = await fetch("/api/member/checkin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: uuid }),
    });
    const data = await res.json();
    if (data.status === "ok") {
      setStatus("CHECKED IN", "ok");
      if (memberCheckinResult) { memberCheckinResult.textContent = `Välkommen ${data.member_name}! #${data.checkin_number}`; memberCheckinResult.className = "guest-checkin-result success"; }
      counterValue.textContent = data.checkin_number;
      presentValue.textContent = data.present;
    } else if (data.status === "checkout") {
      setStatus("CHECKED OUT", "info");
      if (memberCheckinResult) { memberCheckinResult.textContent = `${data.member_name} utcheckad.`; memberCheckinResult.className = "guest-checkin-result"; }
      presentValue.textContent = data.present;
    } else if (data.status === "already_left") {
      if (memberCheckinResult) { memberCheckinResult.textContent = `${data.member_name} har redan lämnat.`; memberCheckinResult.className = "guest-checkin-result"; }
    } else {
      if (memberCheckinResult) { memberCheckinResult.textContent = "Kunde inte checka in."; memberCheckinResult.className = "guest-checkin-result error"; }
    }
  } catch (err) {
    if (memberCheckinResult) { memberCheckinResult.textContent = "Nätverksfel."; memberCheckinResult.className = "guest-checkin-result error"; }
  }
  resetIdleTimer();
  setTimeout(() => { if (memberCheckinResult) { memberCheckinResult.textContent = ""; memberCheckinResult.className = "guest-checkin-result"; } }, 5000);
}

if (memberSearchInput) {
  memberSearchInput.addEventListener("input", () => {
    clearTimeout(memberSearchTimeout);
    memberSearchTimeout = setTimeout(searchMembers, 300);
  });
}

// === Event listeners ===

if (linkBtn) linkBtn.addEventListener("click", linkAndCheckin);
if (linkInput) linkInput.addEventListener("keydown", (e) => { if (e.key === "Enter") linkAndCheckin(); });
if (startButton) startButton.addEventListener("click", startSession);
if (scanPanel && scanPanel.style.display !== "none") initScanner();
if (regSubmit) regSubmit.addEventListener("click", submitRegistration);
if (regCancel) regCancel.addEventListener("click", hideRegisterForm);
if (regTag) regTag.addEventListener("input", validateRegisterForm);
if (regPnr) regPnr.addEventListener("input", validateRegisterForm);
if (idleOverlay) {
  idleOverlay.addEventListener("click", resetIdleTimer);
  idleOverlay.addEventListener("mousemove", resetIdleTimer);
  idleOverlay.addEventListener("touchstart", resetIdleTimer);
}
if (guestCheckinToggle) guestCheckinToggle.addEventListener("click", toggleGuestCheckin);
if (guestCheckinBtn) guestCheckinBtn.addEventListener("click", submitGuestCheckin);
if (guestNameInput) guestNameInput.addEventListener("keydown", (e) => { if (e.key === "Enter") submitGuestCheckin(); });
if (kioskRegBtn) kioskRegBtn.addEventListener("click", toggleGuestSearch);
if (guestSearchBtn) guestSearchBtn.addEventListener("click", searchGuestCheckins);
if (guestSearchInput) guestSearchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") searchGuestCheckins(); });
