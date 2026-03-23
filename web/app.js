const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const messages = document.getElementById("messages");
const chat = document.querySelector(".chat");
const micArea = document.getElementById("mic-area");
const micButton = document.getElementById("mic-button");
const micWarning = document.getElementById("mic-warning");
const storageTitle = document.getElementById("storage-title");
const storageSubtitle = document.getElementById("storage-subtitle");
const operatorBadge = document.getElementById("operator-badge");
const operatorChangeButton = document.getElementById("operator-change-button");
const operatorOverlay = document.getElementById("operator-overlay");
const operatorForm = document.getElementById("operator-form");
const operatorInput = document.getElementById("operator-input");
const operatorError = document.getElementById("operator-error");
const defaultInputPlaceholder = input ? input.placeholder : "";

const params = new URLSearchParams(window.location.search);
const userId = params.get("user_id");
const operatorIdParam = params.get("operator_id");
const callsignParam = params.get("callsign");
const operatorStorageKey = "operator_id";
const maxOperatorIdLength = 64;
let clientId = null;
let operatorId = null;
let clientConfig = {
  audio_web_speech_enabled: true,
  audio_autosend: true,
  audio_web_speech_lang: "uk-UA",
  audio_web_speech_max_seconds: 30,
};
const permissionWarningKey = "zsus_mic_permission_warning";
const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let recognitionTimer = null;
let isListening = false;
let isShowingListeningPlaceholder = false;
let isBusy = false;

function normalizeOperatorId(rawValue) {
  if (typeof rawValue !== "string") {
    return null;
  }
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return null;
  }
  return trimmed.slice(0, maxOperatorIdLength);
}

function clearOperatorParamsFromUrl() {
  if (!window.history || !window.history.replaceState) {
    return;
  }
  if (!params.has("operator_id") && !params.has("callsign")) {
    return;
  }

  const nextParams = new URLSearchParams(params);
  nextParams.delete("operator_id");
  nextParams.delete("callsign");

  const query = nextParams.toString();
  const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
  window.history.replaceState({}, "", nextUrl);
}

function resolveOperatorId() {
  const directOperatorId = normalizeOperatorId(operatorIdParam);
  const directCallsign = normalizeOperatorId(callsignParam);
  const compatibilitySeed = normalizeOperatorId(userId);
  const urlOperatorId = directOperatorId || directCallsign || compatibilitySeed;

  if (urlOperatorId) {
    localStorage.setItem(operatorStorageKey, urlOperatorId);
    if (directOperatorId || directCallsign) {
      clearOperatorParamsFromUrl();
    }
    return urlOperatorId;
  }

  return normalizeOperatorId(localStorage.getItem(operatorStorageKey));
}

function persistOperatorId(value) {
  operatorId = value;
  localStorage.setItem(operatorStorageKey, value);
  updateOperatorUi();
  updateControlsState();
}

function updateOperatorUi() {
  if (operatorBadge) {
    operatorBadge.textContent = operatorId || "—";
    operatorBadge.title = operatorId || "Позивний не задано";
  }
}

function setOperatorError(message) {
  if (!operatorError) {
    return;
  }
  if (!message) {
    operatorError.hidden = true;
    operatorError.textContent = "";
    return;
  }
  operatorError.textContent = message;
  operatorError.hidden = false;
}

function showOperatorOverlay(prefillValue = "") {
  if (!operatorOverlay || !operatorInput) {
    return;
  }
  operatorOverlay.hidden = false;
  operatorInput.value = prefillValue;
  setOperatorError("");
  window.setTimeout(() => {
    operatorInput.focus();
    operatorInput.select();
  }, 0);
}

function hideOperatorOverlay() {
  if (!operatorOverlay) {
    return;
  }
  operatorOverlay.hidden = true;
}

function updateControlsState() {
  const operatorReady = Boolean(operatorId);
  if (input) {
    input.disabled = isBusy || !operatorReady;
  }
  if (sendButton) {
    sendButton.disabled = isBusy || !operatorReady;
  }
  if (micButton) {
    micButton.disabled = isBusy || !operatorReady;
  }
}

async function loadMeta() {
  try {
    const response = await fetch("api/meta");
    const data = await response.json();
    if (response.ok && data && data.ok && data.storage) {
      const title = data.storage.title;
      const subtitle = data.storage.subtitle;
      if (storageTitle && title) {
        storageTitle.textContent = title;
        document.title = `${title} — ZSUS`;
      }
      if (storageSubtitle && subtitle) {
        storageSubtitle.textContent = subtitle;
      }
    }
  } catch (error) {
    // Keep defaults if meta cannot be loaded.
  }
}

loadMeta();

if (userId && userId.trim()) {
  clientId = userId.trim();
  localStorage.setItem("client_id", clientId);
} else {
  const storedClientId = localStorage.getItem("client_id");
  if (storedClientId) {
    clientId = storedClientId;
  }
}

operatorId = resolveOperatorId();
updateOperatorUi();

function appendMessage(text, type) {
  const item = document.createElement("li");
  item.className = `message message--${type}`;
  item.textContent = text;
  messages.appendChild(item);
  scrollToBottom();
  return item;
}

function setBusy(nextBusy) {
  isBusy = nextBusy;
  updateControlsState();
}

function scrollToBottom() {
  if (!chat) {
    return;
  }
  requestAnimationFrame(() => {
    chat.scrollTop = chat.scrollHeight;
  });
}

const observer = new MutationObserver(() => {
  scrollToBottom();
});

observer.observe(messages, {
  childList: true,
  subtree: true,
  characterData: true,
});

async function sendMessage(text, options = {}) {
  if (!operatorId) {
    showOperatorOverlay();
    return;
  }

  setBusy(true);
  appendMessage(text, "user");
  const pending = appendMessage("…", "bot message--pending");

  const payload = { text, operator_id: operatorId };
  if (clientId) {
    payload.client_id = clientId;
  }

  try {
    const response = await fetch("api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok || !data.ok) {
      const message = data && data.message ? data.message : "Помилка запиту";
      pending.textContent = `Помилка: ${message}`;
      pending.classList.remove("message--pending");
      scrollToBottom();
      return;
    }

    if (data.client_id) {
      clientId = data.client_id;
      localStorage.setItem("client_id", clientId);
    }

    pending.textContent = data.reply || "";
    pending.classList.remove("message--pending");
    scrollToBottom();
  } catch (error) {
    pending.textContent = "Помилка: сервер недоступний";
    pending.classList.remove("message--pending");
    scrollToBottom();
  } finally {
    setBusy(false);
    if (!operatorId) {
      showOperatorOverlay();
      return;
    }
    if (options.suppressFocus) {
      input.blur();
      return;
    }
    input.focus();
  }
}

async function loadConfig() {
  try {
    const response = await fetch("api/config");
    const data = await response.json();
    if (response.ok && data && data.ok && data.client) {
      clientConfig = { ...clientConfig, ...data.client };
    }
  } catch (error) {
    // Keep defaults if config cannot be loaded.
  }
}

function updateMicVisibility() {
  if (!micArea || !micButton) {
    return;
  }
  const shouldShow =
    clientConfig.audio_web_speech_enabled && Boolean(SpeechRecognition);
  micArea.hidden = !shouldShow;
}

function showMicWarningOnce(message) {
  if (!micWarning) {
    return;
  }
  const alreadyShown = localStorage.getItem(permissionWarningKey);
  if (alreadyShown) {
    return;
  }
  micWarning.textContent = message;
  micWarning.hidden = false;
  localStorage.setItem(permissionWarningKey, "true");
}

function stopRecognition() {
  if (recognition) {
    recognition.stop();
  }
}

function clearRecognitionTimer() {
  if (recognitionTimer) {
    clearTimeout(recognitionTimer);
    recognitionTimer = null;
  }
}

function cleanupRecognition() {
  clearRecognitionTimer();
  if (micButton) {
    micButton.classList.remove("is-listening");
  }
  setListeningPlaceholder(false);
  recognition = null;
  isListening = false;
  updateControlsState();
}

function setListeningPlaceholder(isActive) {
  if (!input) {
    return;
  }
  if (isActive) {
    if (isShowingListeningPlaceholder) {
      return;
    }
    input.dataset.originalPlaceholder = input.placeholder;
    input.placeholder = "listening...";
    isShowingListeningPlaceholder = true;
  } else if (isShowingListeningPlaceholder) {
    input.placeholder =
      input.dataset.originalPlaceholder || defaultInputPlaceholder;
    delete input.dataset.originalPlaceholder;
    isShowingListeningPlaceholder = false;
  }
}

function startRecognition() {
  if (!operatorId) {
    showOperatorOverlay(operatorId || "");
    return;
  }

  if (!SpeechRecognition || isListening || !micButton || micButton.disabled) {
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = clientConfig.audio_web_speech_lang || "uk-UA";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.continuous = false;

  recognition.onresult = (event) => {
    let transcript = "";
    for (let i = 0; i < event.results.length; i += 1) {
      if (event.results[i].isFinal) {
        transcript += event.results[i][0].transcript;
      }
    }
    const finalText = transcript.trim();
    if (!finalText) {
      return;
    }
    if (clientConfig.audio_autosend) {
      sendMessage(finalText, { suppressFocus: true });
    } else {
      const current = input.value.trim();
      input.value = current ? `${current} ${finalText}` : finalText;
      input.focus();
    }
  };

  recognition.onerror = (event) => {
    if (
      event.error === "not-allowed" ||
      event.error === "permission-denied"
    ) {
      showMicWarningOnce(
        "Доступ до мікрофона заборонено. Дозвольте його в налаштуваннях браузера."
      );
    }
  };

  recognition.onend = () => {
    cleanupRecognition();
  };

  isListening = true;
  if (micButton) {
    micButton.classList.add("is-listening");
  }
  setListeningPlaceholder(true);
  recognition.start();

  const maxSeconds = clientConfig.audio_web_speech_max_seconds || 30;
  recognitionTimer = window.setTimeout(() => {
    stopRecognition();
  }, maxSeconds * 1000);
}

function attachMicHandlers() {
  if (!micButton) {
    return;
  }

  micButton.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    startRecognition();
  });

  micButton.addEventListener("contextmenu", (event) => {
    event.preventDefault();
  });

  ["pointerup", "pointercancel", "pointerleave"].forEach((eventName) => {
    micButton.addEventListener(eventName, (event) => {
      event.preventDefault();
      if (isListening) {
        stopRecognition();
      }
    });
  });
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || !operatorId) {
    if (!operatorId) {
      showOperatorOverlay();
    }
    return;
  }
  input.value = "";
  sendMessage(text);
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    form.requestSubmit();
  }
});

if (operatorChangeButton) {
  operatorChangeButton.addEventListener("click", () => {
    showOperatorOverlay(operatorId || "");
  });
}

if (operatorForm) {
  operatorForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const normalized = normalizeOperatorId(operatorInput.value);
    if (!normalized) {
      setOperatorError("Введи непорожній позивний до 64 символів.");
      operatorInput.focus();
      return;
    }
    persistOperatorId(normalized);
    hideOperatorOverlay();
    input.focus();
  });
}

loadConfig().finally(() => {
  updateMicVisibility();
  attachMicHandlers();
  updateControlsState();
  if (!operatorId) {
    showOperatorOverlay();
    return;
  }
  input.focus();
});
