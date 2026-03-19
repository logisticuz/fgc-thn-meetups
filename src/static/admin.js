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

async function loadAttendance() {
  if (!attendanceContainer) return;
  try {
    const res = await fetch("/api/sessions/attendance");
    const data = await res.json();
    if (!data.open || data.total === 0) {
      attendanceContainer.innerHTML = '<p class="attendance-empty">Ingen aktiv session eller inga incheckade.</p>';
      return;
    }
    const items = data.checkins.map((c) => {
      const time = c.checkin_time ? new Date(c.checkin_time).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" }) : "";
      const outTime = c.checkout_time ? new Date(c.checkout_time).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" }) : "";
      const statusClass = c.checked_out ? "checkout-out" : "checkout-in";
      const statusText = c.checked_out ? `ut ${outTime}` : "här";
      return `<li class="${statusClass}"><span><span class="attendance-number">#${c.number}</span>${c.name}</span><span class="attendance-actions"><span class="attendance-time">${time} · ${statusText}</span><button class="btn-delete" onclick="deleteCheckin(${c.checkin_id})" title="Ta bort">&times;</button></span></li>`;
    });
    attendanceContainer.innerHTML = `<p style="margin-bottom:8px"><span style="color:var(--accent);font-weight:700;">${data.present} här nu</span> <span style="color:var(--muted)">· ${data.total} totalt</span></p><ul class="attendance-list">${items.join("")}</ul>`;
  } catch (err) {
    attendanceContainer.innerHTML = '<p class="attendance-empty">Kunde inte ladda närvarolistan.</p>';
  }
}

async function loadHeadcounts() {
  if (!headcountLog) return;
  try {
    const res = await fetch("/api/headcount");
    const data = await res.json();
    if (!data.headcounts || data.headcounts.length === 0) {
      headcountLog.innerHTML = '<p class="attendance-empty" style="margin-top:10px">Inga registreringar.</p>';
      return;
    }
    const items = data.headcounts.map((hc) => {
      const time = hc.recorded_at ? new Date(hc.recorded_at).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" }) : "";
      return `<li><span class="attendance-number">${hc.count} pers</span><span class="attendance-time">${time}</span></li>`;
    });
    headcountLog.innerHTML = `<ul class="attendance-list" style="margin-top:10px">${items.join("")}</ul>`;
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

loadAttendance();
loadHeadcounts();
setInterval(loadAttendance, 15000);
