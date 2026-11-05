const $ = (selector) => document.querySelector(selector);
const state = { node: "language", language: null, ward_code: null };

document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("active", item === tab));
  document.querySelectorAll(".panel").forEach((panel) => {
    const active = panel.id === tab.dataset.tab;
    panel.classList.toggle("active", active);
    panel.hidden = !active;
  });
}));

async function loadCatalog() {
  const host = $("#broadcasts");
  try {
    const response = await fetch("/api/catalog");
    if (!response.ok) throw new Error("Could not load broadcast catalog");
    const { broadcasts } = await response.json();
    $("#count").textContent = `${broadcasts.length} available`;
    if (!broadcasts.length) {
      host.innerHTML = '<div class="empty">No complete Layer 3 MP3 and cue-sheet pairs were found. Generate a broadcast into the repository output folder, then reload this page.</div>';
      return;
    }
    host.replaceChildren(...broadcasts.map((item) => {
      const card = document.createElement("article");
      card.className = "broadcast-card";
      const info = document.createElement("div");
      const title = document.createElement("h3");
      title.className = "broadcast-name";
      title.textContent = item.ward;
      const meta = document.createElement("p");
      meta.className = "meta";
      meta.textContent = `${item.language_name} · ${item.language.toUpperCase()}`;
      info.append(title, meta);
      const actions = document.createElement("div");
      actions.className = "card-actions";
      const preview = document.createElement("a");
      preview.className = "action";
      preview.href = item.audio_url;
      preview.target = "_blank";
      preview.rel = "noreferrer";
      preview.textContent = "Preview MP3 ↗";
      const cue = document.createElement("a");
      cue.className = "action";
      cue.href = item.script_url;
      cue.textContent = "Cue sheet";
      const pack = document.createElement("a");
      pack.className = "action primary";
      pack.href = item.pack_url;
      pack.textContent = "Download ZIP ↓";
      actions.append(preview, cue, pack);
      card.append(info, actions);
      return card;
    }));
  } catch (error) {
    host.innerHTML = `<div class="empty">${error.message}</div>`;
  }
}

function drawKeypad() {
  const keypad = $("#keypad");
  const keys = [["1", ""], ["2", "ABC"], ["3", "DEF"], ["4", "GHI"], ["5", "JKL"], ["6", "MNO"], ["7", "PQRS"], ["8", "TUV"], ["9", "WXYZ"], ["*", "restart"], ["0", "+"], ["#", ""]];
  keypad.replaceChildren(...keys.map(([digit, letters]) => {
    const button = document.createElement("button");
    button.className = "key";
    button.type = "button";
    button.innerHTML = `${digit}${letters ? `<small>${letters}</small>` : ""}`;
    button.setAttribute("aria-label", `Press ${digit}`);
    button.addEventListener("click", () => press(digit));
    return button;
  }));
}

function setMenu(result) {
  state.node = result.node;
  if (result.language) state.language = result.language;
  if (result.ward_code) state.ward_code = result.ward_code;
  $("#prompt").textContent = result.prompt;
  $("#choices").textContent = (result.options || []).map((option) => {
    if (option.language === "sw") return "1 · Kiswahili";
    if (option.language === "en") return "2 · English";
    return `${option.digit} · ${option.ward}`;
  }).join("\n");
  $("#choices").style.whiteSpace = "pre-line";
  if (result.audio_url) {
    const audio = $("#audio");
    audio.src = result.audio_url;
    audio.hidden = false;
    audio.load();
    audio.play().catch(() => {});
    $("#playing-title").textContent = `${result.ward} · ${result.language.toUpperCase()}`;
    $("#player-help").textContent = result.prompt;
  }
}

async function press(digit) {
  try {
    const response = await fetch("/ivr/keypress", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...state, digit }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Could not process that key");
    setMenu(result);
  } catch (error) {
    $("#prompt").textContent = error.message;
  }
}

function restart() {
  state.node = "language";
  state.language = null;
  state.ward_code = null;
  $("#audio").pause();
  $("#audio").removeAttribute("src");
  $("#audio").hidden = true;
  $("#playing-title").textContent = "Select a menu option";
  $("#player-help").textContent = "Audio will appear here when you select a ward.";
  setMenu({ node: "language", prompt: "Choose language: press 1 for Kiswahili, press 2 for English.", options: [{ digit: "1", language: "sw" }, { digit: "2", language: "en" }] });
}

$("#restart").addEventListener("click", restart);
drawKeypad();
restart();
loadCatalog();
