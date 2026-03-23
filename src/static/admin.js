const startButton = document.getElementById("admin-start");
const endButton = document.getElementById("admin-end");
const attendanceContainer = document.getElementById("attendance-container");
const headcountBtn = document.getElementById("headcount-btn");
const headcountInput = document.getElementById("headcount-input");
const headcountLog = document.getElementById("headcount-log");

if (startButton) {
  startButton.addEventListener("click", async () => {
    const location = document.getElementById("admin-location").value;
    const notes = document.getElementById("admin-notes").value;
    await fetch("/api/sessions/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ location, notes }),
    });
    window.location.reload();
  });
}

if (endButton) {
  endButton.addEventListener("click", async () => {
    await fetch("/api/sessions/end", { method: "POST" });
    window.location.reload();
  });
}

async function deleteCheckin(checkinId) {
  if (!confirm("Ta bort denna incheckning?")) return;
  await fetch(`/api/checkin/${checkinId}`, { method: "DELETE" });
  loadAttendance();
}

function clearChildren(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
}

function el(tag, attrs, children) {
  const node = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "textContent") { node.textContent = v; }
      else if (k.startsWith("on")) { node.addEventListener(k.slice(2), v); }
      else if (k === "className") { node.className = v; }
      else { node.setAttribute(k, v); }
    }
  }
  if (children) {
    for (const child of children) {
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    }
  }
  return node;
}

async function loadAttendance() {
  if (!attendanceContainer) return;
  try {
    const res = await fetch("/api/sessions/attendance");
    const data = await res.json();
    if (!data.open || data.total === 0) {
      clearChildren(attendanceContainer);
      attendanceContainer.appendChild(el("p", { className: "attendance-empty", textContent: "Ingen aktiv session eller inga incheckade." }));
      return;
    }

    const summaryP = el("p", { style: "margin-bottom:8px" }, [
      el("span", { style: "color:var(--accent);font-weight:700;", textContent: `${data.present} här nu` }),
      " ",
      el("span", { style: "color:var(--muted)", textContent: `· ${data.total} totalt` }),
    ]);

    const ul = el("ul", { className: "attendance-list" });
    for (const c of data.checkins) {
      const time = c.checkin_time ? new Date(c.checkin_time).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" }) : "";
      const outTime = c.checkout_time ? new Date(c.checkout_time).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" }) : "";
      const statusClass = c.checked_out ? "checkout-out" : "checkout-in";
      const statusText = c.checked_out ? `ut ${outTime}` : "här";

      const nameChildren = [
        el("span", { className: "attendance-number", textContent: `#${c.number}` }),
        c.name,
      ];
      if (c.is_guest) {
        nameChildren.push(el("span", { className: "guest-tag", textContent: "(gäst)" }));
      }

      const actionChildren = [
        el("span", { className: "attendance-time", textContent: `${time} · ${statusText}` }),
      ];
      if (c.is_guest && !c.checked_out) {
        actionChildren.push(el("button", {
          className: "btn-register",
          textContent: "Bli medlem",
          onclick: () => showAdminRegisterForm(c.checkin_id, c.name),
        }));
      }
      actionChildren.push(el("button", { className: "btn-delete", title: "Ta bort", textContent: "\u00d7", onclick: () => deleteCheckin(c.checkin_id) }));

      const li = el("li", { className: statusClass }, [
        el("span", {}, nameChildren),
        el("span", { className: "attendance-actions" }, actionChildren),
      ]);
      ul.appendChild(li);
    }

    clearChildren(attendanceContainer);
    attendanceContainer.appendChild(summaryP);
    attendanceContainer.appendChild(ul);
  } catch (err) {
    clearChildren(attendanceContainer);
    attendanceContainer.appendChild(el("p", { className: "attendance-empty", textContent: "Kunde inte ladda närvarolistan." }));
  }
}

async function loadHeadcounts() {
  if (!headcountLog) return;
  try {
    const res = await fetch("/api/headcount");
    const data = await res.json();
    if (!data.headcounts || data.headcounts.length === 0) {
      clearChildren(headcountLog);
      headcountLog.appendChild(el("p", { className: "attendance-empty", style: "margin-top:10px", textContent: "Inga registreringar." }));
      return;
    }
    const ul = el("ul", { className: "attendance-list", style: "margin-top:10px" });
    for (const hc of data.headcounts) {
      const time = hc.recorded_at ? new Date(hc.recorded_at).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" }) : "";
      ul.appendChild(el("li", {}, [
        el("span", { className: "attendance-number", textContent: `${hc.count} pers` }),
        el("span", { className: "attendance-time", textContent: time }),
      ]));
    }
    clearChildren(headcountLog);
    headcountLog.appendChild(ul);
  } catch (err) { /* ignore */ }
}

if (headcountBtn) {
  headcountBtn.addEventListener("click", async () => {
    const count = parseInt(headcountInput.value, 10);
    if (isNaN(count) || count < 0) return;
    await fetch("/api/headcount", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ count }),
    });
    headcountInput.value = "";
    loadHeadcounts();
  });
}

// === Guest registration (admin) ===

const adminRegModal = document.getElementById("admin-register-modal");
const adminRegTag = document.getElementById("admin-reg-tag");
const adminRegPnr = document.getElementById("admin-reg-pnr");
const adminRegPhone = document.getElementById("admin-reg-phone");
const adminRegEmail = document.getElementById("admin-reg-email");
const adminRegSubmit = document.getElementById("admin-reg-submit");
const adminRegCancel = document.getElementById("admin-reg-cancel");
const adminRegResult = document.getElementById("admin-reg-result");
const adminRegPnrError = document.getElementById("admin-reg-pnr-error");
const adminRegGuestInfo = document.getElementById("admin-reg-guest-info");

let adminPendingReg = null;

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

function validateAdminRegForm() {
  const tag = adminRegTag ? adminRegTag.value.trim() : "";
  const pnr = adminRegPnr ? adminRegPnr.value.trim() : "";
  const pnrResult = pnr ? validatePersonnummer(pnr) : { valid: false, error: "" };
  if (adminRegPnrError) adminRegPnrError.textContent = pnr && !pnrResult.valid ? pnrResult.error : "";
  if (adminRegSubmit) adminRegSubmit.disabled = !(tag.length > 0 && pnrResult.valid);
}

function showAdminRegisterForm(checkinId, guestName) {
  adminPendingReg = { checkinId, guestName };
  if (adminRegGuestInfo) adminRegGuestInfo.textContent = `Registrera ${guestName} som medlem i FGC Trollhättan`;
  if (adminRegTag) adminRegTag.value = "";
  if (adminRegPnr) adminRegPnr.value = "";
  if (adminRegPhone) adminRegPhone.value = "";
  if (adminRegEmail) adminRegEmail.value = "";
  if (adminRegResult) { adminRegResult.textContent = ""; adminRegResult.className = "register-result"; }
  if (adminRegPnrError) adminRegPnrError.textContent = "";
  if (adminRegSubmit) adminRegSubmit.disabled = true;
  if (adminRegModal) adminRegModal.style.display = "flex";
  if (adminRegTag) adminRegTag.focus();
}

function hideAdminRegisterForm() {
  adminPendingReg = null;
  if (adminRegModal) adminRegModal.style.display = "none";
}

async function submitAdminRegistration() {
  if (!adminPendingReg) return;
  const tag = adminRegTag ? adminRegTag.value.trim() : "";
  const personnummer = adminRegPnr ? sanitizePersonnummer(adminRegPnr.value) : "";
  const telephone = adminRegPhone ? adminRegPhone.value.trim() : "";
  const email = adminRegEmail ? adminRegEmail.value.trim() : "";
  if (!tag || !personnummer) return;

  if (adminRegSubmit) adminRegSubmit.disabled = true;
  if (adminRegResult) { adminRegResult.textContent = "Registrerar..."; adminRegResult.className = "register-result"; }

  try {
    const res = await fetch("/api/guest/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        checkin_id: String(adminPendingReg.checkinId),
        tag, personnummer, telephone, email,
      }),
    });
    const data = await res.json();
    if (data.success) {
      if (adminRegResult) { adminRegResult.textContent = `Välkommen som medlem, ${tag}!`; adminRegResult.className = "register-result success"; }
      setTimeout(() => { hideAdminRegisterForm(); loadAttendance(); }, 2000);
    } else {
      if (adminRegResult) { adminRegResult.textContent = data.error || data.message || "Registreringen misslyckades"; adminRegResult.className = "register-result error"; }
      if (adminRegSubmit) adminRegSubmit.disabled = false;
    }
  } catch (err) {
    if (adminRegResult) { adminRegResult.textContent = "Nätverksfel — försök igen"; adminRegResult.className = "register-result error"; }
    if (adminRegSubmit) adminRegSubmit.disabled = false;
  }
}

if (adminRegSubmit) adminRegSubmit.addEventListener("click", submitAdminRegistration);
if (adminRegCancel) adminRegCancel.addEventListener("click", hideAdminRegisterForm);
if (adminRegTag) adminRegTag.addEventListener("input", validateAdminRegForm);
if (adminRegPnr) adminRegPnr.addEventListener("input", validateAdminRegForm);

loadAttendance();
loadHeadcounts();
setInterval(loadAttendance, 15000);
