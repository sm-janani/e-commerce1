const API_BASE = "http://localhost:8000";
const sessionId = crypto.randomUUID();

const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");
const typingEl = document.getElementById("typing");

function addBubble(text, sender, opts = {}) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${sender}${opts.escalated ? " escalated" : ""}`;
  bubble.textContent = text;
  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addToolTag(toolCalls) {
  if (!toolCalls || toolCalls.length === 0) return;
  const names = toolCalls.map((t) => t.tool_name).join(", ");
  const tag = document.createElement("div");
  tag.className = "tool-tag";
  tag.textContent = `⚙ used: ${names}`;
  messagesEl.appendChild(tag);
}

async function sendMessage(message) {
  typingEl.hidden = false;
  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });

    if (!res.ok) {
      throw new Error(`Server returned ${res.status}`);
    }

    const data = await res.json();
    typingEl.hidden = true;
    addToolTag(data.tool_calls);
    addBubble(data.reply, "agent", { escalated: data.escalated });

    if (data.escalated) {
      addBubble(
        "This conversation has been flagged for a human agent who will follow up shortly.",
        "agent",
        { escalated: true }
      );
    }
  } catch (err) {
    typingEl.hidden = true;
    addBubble(
      "Sorry, something went wrong reaching support. Please try again in a moment.",
      "agent"
    );
    console.error(err);
  }
}

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = inputEl.value.trim();
  if (!message) return;
  addBubble(message, "user");
  inputEl.value = "";
  sendMessage(message);
});

// Greet the user on load
addBubble(
  "Hi! I'm Aria, your support assistant. I can help with order tracking, returns, product availability, and store policies. How can I help today?",
  "agent"
);
