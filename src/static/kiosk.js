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

let lastScan = { value: null, time: 0 };
let pendingCardId = null;
let scanner = null;
let idleTimer = null;

const IDLE_DELAY_MS = 10000;

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
  const location = document.getElementById("location").value;
  const notes = document.getElementById("notes").value;
  const res = await fetch("/api/sessions/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ location, notes }),
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
  } else if (data.status === "checkout") {
    setStatus("UTCHECKAD", "info");
    scanResultEl.textContent = `Hej d\u00e5 ${data.member_name}! Vi ses n\u00e4sta g\u00e5ng`;
    updateCounters(undefined, data.present);
  } else if (data.status === "already_left") {
    setStatus("REDAN UTCHECKAD", "warn");
    scanResultEl.textContent = `${data.member_name} har redan checkat ut`;
  } else if (data.status === "unknown") {
    setStatus("OK\u00c4ND", "warn");
    scanResultEl.textContent = "QR-koden k\u00e4nns inte igen.";
    showLinkForm(data.card_id);
  } else if (data.status === "no_session") {
    setStatus("INGEN SESSION", "warn");
    scanResultEl.textContent = "Ingen aktiv session.";
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

if (linkBtn) linkBtn.addEventListener("click", linkAndCheckin);
if (linkInput) linkInput.addEventListener("keydown", (e) => { if (e.key === "Enter") linkAndCheckin(); });
if (startButton) startButton.addEventListener("click", startSession);
if (scanPanel && scanPanel.style.display !== "none") initScanner();
