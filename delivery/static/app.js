const $ = (selector) => document.querySelector(selector);
const state = { node: "language", language: null, ward_code: null };
let availableLanguages = [];

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
    availableLanguages = [...new Set(broadcasts.map((item) => item.language))];
    restart();
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
      const preview = document.createElement("audio");
      preview.className = "broadcast-audio";
      preview.controls = true;
      preview.preload = "none";
      preview.src = item.audio_url;
      preview.setAttribute("aria-label", `Play ${item.ward} ${item.language_name} advisory`);
      const cue = document.createElement("a");
      cue.className = "action";
      cue.href = item.script_url;
      cue.textContent = "Cue sheet";
      const pack = document.createElement("a");
      pack.className = "action primary";
      pack.href = item.pack_url;
      pack.download = `${item.ward_code}_${item.language}_radio_pack.zip`;
      pack.textContent = "Download ZIP ↓";
      const downloadStatus = document.createElement("p");
      downloadStatus.className = "download-status";
      downloadStatus.setAttribute("role", "status");
      downloadStatus.setAttribute("aria-live", "polite");
      pack.addEventListener("click", async (event) => {
        event.preventDefault();
        pack.setAttribute("aria-busy", "true");
        pack.textContent = "Preparing download…";
        downloadStatus.textContent = "Preparing your radio pack. This page will stay open.";
        try {
          const response = await fetch(item.pack_url);
          if (!response.ok) throw new Error(`Download failed (${response.status})`);
          const objectUrl = URL.createObjectURL(await response.blob());
          const downloadLink = document.createElement("a");
          downloadLink.href = objectUrl;
          downloadLink.download = `${item.ward_code}_${item.language}_radio_pack.zip`;
          downloadLink.hidden = true;
          document.body.append(downloadLink);
          downloadLink.click();
          downloadLink.remove();
          window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
          downloadStatus.textContent = "Radio pack download started. You can keep using this page.";
        } catch (error) {
          downloadStatus.textContent = `Could not download the pack: ${error.message}`;
        } finally {
          pack.removeAttribute("aria-busy");
          pack.textContent = "Download ZIP ↓";
        }
      });
      actions.append(cue, pack);
      card.append(info, preview, actions, downloadStatus);
      return card;
    }));
  } catch (error) {
      const message = document.createElement("div");
      message.className = "empty";
      message.textContent = error.message;
      host.replaceChildren(message);
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
  const choices = result.options || [];
  $("#choices").replaceChildren(...choices.map((option) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "choice-key";
    const label = option.language === "sw" ? "Kiswahili" : option.language === "en" ? "English" : option.ward;
    button.textContent = `${option.digit} · ${label}`;
    button.setAttribute("aria-label", `Press ${option.digit} for ${label}`);
    button.addEventListener("click", () => press(option.digit));
    return button;
  }));
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
  const options = [
    ...(availableLanguages.includes("sw") ? [{ digit: "1", language: "sw" }] : []),
    ...(availableLanguages.includes("en") ? [{ digit: "2", language: "en" }] : []),
  ];
  setMenu({
    node: "language",
    prompt: options.length ? "Choose a language for the advisory." : "No audio advisories are available yet. Load or generate a Layer 3 broadcast, then reload this page.",
    options,
  });
}

document.addEventListener("keydown", (event) => {
  if (!$("#ivr").classList.contains("active")) return;
  if (event.target.closest("input, select, textarea, audio")) return;
  if (/^[0-9*#]$/.test(event.key)) {
    event.preventDefault();
    press(event.key);
  }
});

$("#restart").addEventListener("click", restart);
drawKeypad();
restart();
loadCatalog();
