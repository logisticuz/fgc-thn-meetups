const startButton = document.getElementById("start-session");
const startPanel = document.getElementById("session-start");
const scanPanel = document.getElementById("scan-panel");
const statusEl = document.getElementById("status");
const scanResultEl = document.getElementById("scan-result");
const scanHintEl = document.getElementById("scan-hint");
const video = document.getElementById("camera");
const counterValue = document.getElementById("counter-value");
const presentValue = document.getElementById("present-value");

let detector = null;
let scanning = false;
let lastScan = { value: null, time: 0 };

function setStatus(text, level) {
  statusEl.textContent = text;
  statusEl.className = "status";
  if (level) {
    statusEl.classList.add(level);
  }
}

function updateCounters(total, present) {
  if (counterValue && total !== undefined) counterValue.textContent = total;
  if (presentValue && present !== undefined) presentValue.textContent = present;
}

async function fetchAttendance() {
  try {
    const res = await fetch("/api/sessions/attendance");
    const data = await res.json();
    if (data.open) {
      updateCounters(data.total, data.present);
    }
  } catch (err) {
    // ignore
  }
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
    scanResultEl.textContent = "Failed to start session.";
    return;
  }
  startPanel.style.display = "none";
  scanPanel.style.display = "block";
  initScanner();
}

async function initScanner() {
  await fetchAttendance();

  if (!("BarcodeDetector" in window)) {
    setStatus("NO SCANNER", "warn");
    scanHintEl.textContent = "BarcodeDetector not supported. Use manual check-in.";
    return;
  }

  detector = new BarcodeDetector({ formats: ["qr_code"] });
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    video.srcObject = stream;
    scanning = true;
    scanLoop();
  } catch (err) {
    setStatus("CAMERA BLOCKED", "warn");
    scanHintEl.textContent = "Allow camera access to scan QR codes.";
  }
}

async function scanLoop() {
  if (!scanning || !detector) return;
  try {
    const barcodes = await detector.detect(video);
    if (barcodes.length > 0) {
      const value = barcodes[0].rawValue;
      const now = Date.now();
      if (value !== lastScan.value || now - lastScan.time > 3000) {
        lastScan = { value, time: now };
        await sendCheckin(value);
      }
    }
  } catch (err) {
    // ignore transient errors
  }
  requestAnimationFrame(scanLoop);
}

async function sendCheckin(qrData) {
  setStatus("SCANNED", "info");
  const res = await fetch("/api/checkin", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ qr_data: qrData }),
  });

  const data = await res.json();
  if (data.status === "ok") {
    setStatus("INCHECKAD", "ok");
    scanResultEl.textContent = `Välkommen ${data.member_name}! Du är #${data.checkin_number} idag`;
    updateCounters(data.checkin_number, data.present);
  } else if (data.status === "checkout") {
    setStatus("UTCHECKAD", "info");
    scanResultEl.textContent = `Hej då ${data.member_name}! Vi ses nästa gång`;
    updateCounters(undefined, data.present);
  } else if (data.status === "already_left") {
    setStatus("REDAN UTCHECKAD", "warn");
    scanResultEl.textContent = `${data.member_name} har redan checkat ut`;
  } else if (data.status === "unknown") {
    setStatus("OKÄND", "warn");
    scanResultEl.textContent = "QR-koden känns inte igen. Kontakta arrangören.";
  } else if (data.status === "no_session") {
    setStatus("INGEN SESSION", "warn");
    scanResultEl.textContent = "Ingen aktiv session.";
  } else {
    setStatus("FEL", "warn");
    scanResultEl.textContent = "Scanningsfel.";
  }
}

if (startButton) {
  startButton.addEventListener("click", startSession);
}

if (scanPanel && scanPanel.style.display !== "none") {
  initScanner();
}
