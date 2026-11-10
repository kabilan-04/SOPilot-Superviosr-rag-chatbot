const thread = document.getElementById("thread");
const form = document.getElementById("ask-form");
const input = document.getElementById("question");
const askBtn = document.getElementById("ask-btn");
const chips = document.getElementById("chips");
const chipRow = document.getElementById("chip-row");
const clearBtn = document.getElementById("clear-btn");

const chatHistory = [];

function scrollToBottom() {
  requestAnimationFrame(() => {
    thread.scrollTop = thread.scrollHeight;
  });
}

function addUser(text) {
  const el = document.createElement("div");
  el.className = "bubble user";
  el.textContent = text;
  thread.appendChild(el);
  scrollToBottom();
}

function addPending() {
  const el = document.createElement("div");
  el.className = "card pending";
  el.textContent = "Looking in the plant documents…";
  thread.appendChild(el);
  scrollToBottom();
  return el;
}

function sourceLine(match, inDocs) {
  if (!match) return "";
  const label = inDocs
    ? `${match.title}${match.section ? ", " + match.section : ""}`
    : `Closest match: ${match.title}${match.section ? ", " + match.section : ""}`;
  const pill = match.status === "current"
    ? '<span class="pill current">Current</span>'
    : match.status === "superseded"
      ? '<span class="pill superseded">Superseded</span>'
      : "";
  return `<div class="source"><span>📄</span><span>${label} ${pill}</span></div>`;
}

function addAnswer(data) {
  const inDocs = Boolean(data.in_documents);
  const card = document.createElement("div");
  card.className = "card";
  const warning = data.warning
    ? `<p class="warning">${escapeHtml(data.warning)}</p>`
    : "";

  const isClarification = Boolean(data.clarification);

  const badgeClass = inDocs ? "ok" : (isClarification ? "clarify" : "miss");
  const badgeText = inDocs
    ? "Answered from documents"
    : (isClarification ? "Need more context" : "Not in the documents");

  card.innerHTML = `
    <div class="badge ${badgeClass}">${badgeText}</div>
    <p class="answer">${escapeHtml(data.answer || "")}</p>
    ${warning}
    ${sourceLine(data.closest_match, inDocs)}
  `;
  thread.appendChild(card);
  scrollToBottom();
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function ask(question) {
  addUser(question);
  chips.classList.add("hidden");
  const pending = addPending();
  askBtn.disabled = true;
  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        history: chatHistory.slice(-4),
      }),
    });
    const data = await res.json();
    pending.remove();
    if (!res.ok) {
      addAnswer({
        in_documents: false,
        answer: data.detail || "Could not answer just now.",
        warning: null,
        closest_match: null,
      });
    } else {
      addAnswer(data);
      if (data.answer) {
        chatHistory.push({ role: "user", content: question });
        chatHistory.push({ role: "assistant", content: data.answer });
      }
    }
    chips.classList.remove("hidden");
  } catch (err) {
    pending.remove();
    addAnswer({
      in_documents: false,
      answer: "Cannot reach SOPilot on this laptop. Check Wi-Fi and that the app is running.",
      warning: null,
      closest_match: null,
    });
  } finally {
    askBtn.disabled = false;
    scrollToBottom();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;
  input.value = "";
  ask(q);
});

if (clearBtn) {
  clearBtn.addEventListener("click", () => {
    thread.innerHTML = "";
    chatHistory.length = 0;
    chips.classList.remove("hidden");
    input.value = "";
    input.focus();
  });
}

async function loadChips() {
  try {
    const res = await fetch("/api/suggestions");
    const data = await res.json();
    chipRow.innerHTML = "";
    data.suggestions.forEach((text) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip";
      b.textContent = text;
      b.addEventListener("click", () => ask(text));
      chipRow.appendChild(b);
    });
    chips.classList.remove("hidden");
  } catch (err) {
    console.error("Could not load chips:", err);
  }
}

loadChips();
