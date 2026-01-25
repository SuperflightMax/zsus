const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const messages = document.getElementById("messages");
const chat = document.querySelector(".chat");
const micArea = document.getElementById("mic-area");
const micButton = document.getElementById("mic-button");
const micWarning = document.getElementById("mic-warning");

const params = new URLSearchParams(window.location.search);
const userId = params.get("user_id");
let clientId = null;
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

if (userId && userId.trim()) {
  clientId = userId.trim();
  localStorage.setItem("client_id", clientId);
} else {
  const storedClientId = localStorage.getItem("client_id");
  if (storedClientId) {
    clientId = storedClientId;
  }
}

function appendMessage(text, type) {
  const item = document.createElement("li");
  item.className = `message message--${type}`;
  item.textContent = text;
  messages.appendChild(item);
  scrollToBottom();
  return item;
}

function setBusy(isBusy) {
  input.disabled = isBusy;
  sendButton.disabled = isBusy;
  if (micButton) {
    micButton.disabled = isBusy;
  }
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

async function sendMessage(text) {
  setBusy(true);
  appendMessage(text, "user");
  const pending = appendMessage("…", "bot message--pending");

  const payload = { text };
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
  recognition = null;
  isListening = false;
}

function startRecognition() {
  if (!SpeechRecognition || isListening) {
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
      sendMessage(finalText);
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
  if (!text) {
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

loadConfig().finally(() => {
  updateMicVisibility();
  attachMicHandlers();
});

input.focus();
