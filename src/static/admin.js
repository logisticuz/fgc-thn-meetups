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

      const li = el("li", { className: statusClass }, [
        el("span", {}, [
          el("span", { className: "attendance-number", textContent: `#${c.number}` }),
          c.name,
        ]),
        el("span", { className: "attendance-actions" }, [
          el("span", { className: "attendance-time", textContent: `${time} · ${statusText}` }),
          el("button", { className: "btn-delete", title: "Ta bort", textContent: "\u00d7", onclick: () => deleteCheckin(c.checkin_id) }),
        ]),
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

loadAttendance();
loadHeadcounts();
setInterval(loadAttendance, 15000);
