const startButton = document.getElementById("admin-start");
const endButton = document.getElementById("admin-end");
const attendanceContainer = document.getElementById("attendance-container");
const headcountBtn = document.getElementById("headcount-btn");
const headcountInput = document.getElementById("headcount-input");
const headcountLog = document.getElementById("headcount-log");
const liveStatus = document.getElementById("admin-live-status");
const livePresent = document.getElementById("admin-live-present");
const liveTotal = document.getElementById("admin-live-total");

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

function setLiveOverview(data) {
  if (livePresent && data && data.present !== undefined) livePresent.textContent = String(data.present);
  if (liveTotal && data && data.total !== undefined) liveTotal.textContent = String(data.total);
  if (liveStatus) {
    if (data && data.open) liveStatus.textContent = "Session aktiv";
    else liveStatus.textContent = "Ingen aktiv session";
  }
}

async function loadAttendance() {
  if (!attendanceContainer) return;
  try {
    const res = await fetch("/api/sessions/attendance");
    const data = await res.json();
    setLiveOverview(data);
    if (!data.open || data.total === 0) {
      clearChildren(attendanceContainer);
      attendanceContainer.appendChild(el("p", { className: "attendance-empty", textContent: "Ingen aktiv session eller inga incheckade." }));
      return;
    }

    const summaryP = el("p", { className: "attendance-summary" }, [
      el("span", { className: "attendance-summary-present", textContent: `${data.present} här nu` }),
      " ",
      el("span", { className: "attendance-summary-total", textContent: `· ${data.total} totalt` }),
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
    setLiveOverview({ open: false, present: 0, total: 0 });
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

if (headcountInput) {
  headcountInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") headcountBtn?.click();
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

// === Tabs ===
document.querySelectorAll(".admin-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".admin-tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".admin-tab-content").forEach((c) => c.classList.remove("active"));
    tab.classList.add("active");
    const target = document.getElementById(tab.dataset.tab);
    if (target) target.classList.add("active");
  });
});

// === Revenue ===
const revenueBtn = document.getElementById("revenue-btn");
const revenueInput = document.getElementById("revenue-input");
const revenueStatus = document.getElementById("revenue-status");

async function loadRevenue() {
  if (!revenueInput) return;
  try {
    const res = await fetch("/api/kiosk-revenue");
    const data = await res.json();
    if (data.amount > 0) {
      revenueInput.value = data.amount;
      revenueStatus.textContent = `Sparat: ${data.amount} kr`;
      revenueStatus.className = "revenue-status saved";
    }
  } catch (e) { /* ignore */ }
}

if (revenueBtn) {
  revenueBtn.addEventListener("click", async () => {
    const amount = parseFloat(revenueInput.value);
    if (isNaN(amount) || amount < 0) return;
    try {
      const res = await fetch("/api/kiosk-revenue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount }),
      });
      const data = await res.json();
      if (data.status === "ok") {
        revenueStatus.textContent = `Sparat: ${amount} kr`;
        revenueStatus.className = "revenue-status saved";
      } else {
        revenueStatus.textContent = "Ingen aktiv session";
        revenueStatus.className = "revenue-status";
      }
    } catch (e) {
      revenueStatus.textContent = "Kunde inte spara";
      revenueStatus.className = "revenue-status";
    }
  });
}

if (revenueInput) {
  revenueInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") revenueBtn?.click();
  });
}

loadRevenue();

// === Calendar ===
const calGrid = document.getElementById("cal-grid");
if (calGrid) {
  const calTitle = document.getElementById("cal-title");
  const calDetail = document.getElementById("cal-detail");
  const calPrev = document.getElementById("cal-prev");
  const calNext = document.getElementById("cal-next");
  const MONTHS_SV = ["Januari","Februari","Mars","April","Maj","Juni","Juli","Augusti","September","Oktober","November","December"];
  const DAYS_SV = ["Mån","Tis","Ons","Tor","Fre","Lör","Sön"];

  let calYear = new Date().getFullYear();
  let calMonth = new Date().getMonth() + 1;

  async function renderCalendar(year, month) {
    calTitle.textContent = `${MONTHS_SV[month - 1]} ${year}`;
    calDetail.style.display = "none";
    clearChildren(calGrid);

    for (const d of DAYS_SV) {
      calGrid.appendChild(el("div", { className: "calendar-weekday", textContent: d }));
    }

    let sessions = {};
    try {
      const res = await fetch(`/api/calendar?year=${year}&month=${month}`);
      const data = await res.json();
      sessions = data.sessions || {};
    } catch (e) { /* ignore */ }

    const firstDow = (new Date(year, month - 1, 1).getDay() + 6) % 7;
    const daysInMonth = new Date(year, month, 0).getDate();
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,"0")}-${String(today.getDate()).padStart(2,"0")}`;

    for (let i = 0; i < firstDow; i++) {
      calGrid.appendChild(el("div", { className: "calendar-day empty" }));
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(month).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
      const daySessions = sessions[dateStr];
      const has = daySessions && daySessions.length > 0;
      let cls = "calendar-day";
      if (has) cls += " has-session";
      if (dateStr === todayStr) cls += " today";

      const dayEl = el("div", { className: cls, textContent: String(d) });
      if (has) {
        dayEl.appendChild(el("span", { className: "session-dot" }));
        dayEl.addEventListener("click", () => {
          document.querySelectorAll(".calendar-day.selected").forEach(x => x.classList.remove("selected"));
          dayEl.classList.add("selected");
          showDayDetail(daySessions[0].session_id, dateStr);
        });
      }
      calGrid.appendChild(dayEl);
    }
  }

  async function showDayDetail(sessionId, dateStr) {
    calDetail.style.display = "none";
    try {
      const res = await fetch(`/api/calendar/day?session_id=${sessionId}`);
      const data = await res.json();
      clearChildren(calDetail);

      const d = new Date(dateStr + "T12:00:00");
      const dateTitle = d.toLocaleDateString("sv-SE", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

      const header = el("div", { className: "calendar-detail-header" }, [
        el("h3", { textContent: dateTitle.charAt(0).toUpperCase() + dateTitle.slice(1) }),
        el("button", { className: "calendar-detail-close", textContent: "\u00d7", onclick: () => { calDetail.style.display = "none"; document.querySelectorAll(".calendar-day.selected").forEach(x => x.classList.remove("selected")); } }),
      ]);

      const startTime = data.start_time ? new Date(data.start_time).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" }) : "-";
      const endTime = data.end_time ? new Date(data.end_time).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" }) : "pågår";
      let durationText = "-";
      if (data.duration_minutes) {
        const h = Math.floor(data.duration_minutes / 60);
        const m = data.duration_minutes % 60;
        durationText = h > 0 ? `${h}h ${m}m` : `${m}m`;
      }

      const meta = el("div", { className: "calendar-detail-meta" }, [
        el("div", { className: "meta-item" }, [
          el("span", { className: "meta-label", textContent: "Deltagare" }),
          el("span", { className: "meta-value", textContent: String(data.total_checkins) }),
        ]),
        el("div", { className: "meta-item" }, [
          el("span", { className: "meta-label", textContent: "Peak headcount" }),
          el("span", { className: "meta-value", textContent: String(data.peak_headcount) }),
        ]),
        el("div", { className: "meta-item" }, [
          el("span", { className: "meta-label", textContent: "Tid" }),
          el("span", { className: "meta-value", textContent: `${startTime} – ${endTime}` }),
        ]),
        el("div", { className: "meta-item" }, [
          el("span", { className: "meta-label", textContent: "Längd" }),
          el("span", { className: "meta-value", textContent: durationText }),
        ]),
      ]);

      if (data.kiosk_revenue > 0) {
        meta.appendChild(el("div", { className: "meta-item" }, [
          el("span", { className: "meta-label", textContent: "Kassa" }),
          el("span", { className: "meta-value", textContent: `${data.kiosk_revenue} kr` }),
        ]));
      }

      const listItems = (data.checkins || []).map(c => {
        const t = c.checkin_time ? new Date(c.checkin_time).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" }) : "";
        return el("li", {}, [
          el("span", { className: "checkin-name", textContent: c.name }),
          el("span", { className: "checkin-time", textContent: t }),
        ]);
      });
      const list = el("ul", { className: "calendar-checkin-list" }, listItems);

      calDetail.appendChild(header);
      calDetail.appendChild(meta);
      if (listItems.length > 0) {
        calDetail.appendChild(el("div", { className: "meta-label", style: "margin-bottom:8px", textContent: "Deltagarlista" }));
        calDetail.appendChild(list);
      }
      calDetail.style.display = "block";
    } catch (e) { /* ignore */ }
  }

  calPrev.addEventListener("click", () => {
    calMonth--;
    if (calMonth < 1) { calMonth = 12; calYear--; }
    renderCalendar(calYear, calMonth);
  });

  calNext.addEventListener("click", () => {
    calMonth++;
    if (calMonth > 12) { calMonth = 1; calYear++; }
    renderCalendar(calYear, calMonth);
  });

  renderCalendar(calYear, calMonth);
}

loadAttendance();
loadHeadcounts();
setInterval(loadAttendance, 15000);
