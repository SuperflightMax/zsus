const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const messages = document.getElementById("messages");
const chat = document.querySelector(".chat");

const params = new URLSearchParams(window.location.search);
const userId = params.get("user_id");
let clientId = null;

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
  if (chat) {
    requestAnimationFrame(() => {
      chat.scrollTop = chat.scrollHeight;
    });
  }
  return item;
}

function setBusy(isBusy) {
  input.disabled = isBusy;
  sendButton.disabled = isBusy;
}

async function sendMessage(text) {
  setBusy(true);
  appendMessage(text, "user");
  const pending = appendMessage("…", "bot message--pending");

  const payload = { text };
  if (clientId) {
    payload.client_id = clientId;
  }

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok || !data.ok) {
      const message = data && data.message ? data.message : "Помилка запиту";
      pending.textContent = `Помилка: ${message}`;
      pending.classList.remove("message--pending");
      return;
    }

    if (data.client_id) {
      clientId = data.client_id;
      localStorage.setItem("client_id", clientId);
    }

    pending.textContent = data.reply || "";
    pending.classList.remove("message--pending");
  } catch (error) {
    pending.textContent = "Помилка: сервер недоступний";
    pending.classList.remove("message--pending");
  } finally {
    setBusy(false);
    input.focus();
  }
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

input.focus();
