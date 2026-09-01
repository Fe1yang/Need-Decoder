const scenarios = {
  retreat: [
    "I'm looking for Men's Walking Shoes. I need them for a company retreat with lots of walking.",
    "Some activities are outdoors, but we also have a business-casual dinner.",
  ],
  override: [
    "I'm looking for Women's Walking Shoes. I would prefer leather.",
    "Actually, ignore my earlier preference. What I need is breathable mesh for hot weather.",
  ],
};

const state = {
  sessionId: `web-${Date.now()}`,
  turn: 0,
  busy: false,
};

const elements = {
  form: document.querySelector("#chat-form"),
  input: document.querySelector("#message-input"),
  sendButton: document.querySelector("#send-button"),
  resetButton: document.querySelector("#reset-button"),
  messages: document.querySelector("#messages"),
  recommendations: document.querySelector("#recommendations"),
  intent: document.querySelector("#intent-value"),
  category: document.querySelector("#category-value"),
  constraintList: document.querySelector("#constraint-list"),
  needList: document.querySelector("#need-list"),
  constraintCount: document.querySelector("#constraint-count"),
  needCount: document.querySelector("#need-count"),
  override: document.querySelector("#override-value"),
  budget: document.querySelector("#budget-value"),
  turn: document.querySelector("#turn-indicator"),
  resultCount: document.querySelector("#result-count"),
};

async function api(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Request failed");
  return result;
}

function addMessage(role, content, loading = false) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "YOU" : "ND";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (loading) {
    bubble.innerHTML = '<span class="loading-dots"><i></i><i></i><i></i></span>';
    wrapper.dataset.loading = "true";
  } else {
    bubble.textContent = content;
  }
  wrapper.append(avatar, bubble);
  elements.messages.append(wrapper);
  elements.messages.scrollTop = elements.messages.scrollHeight;
  return wrapper;
}

function renderState(snapshot) {
  elements.intent.textContent = snapshot.intent === "buying" ? "Buying" : "Browsing";
  elements.category.textContent = snapshot.category || "Waiting for a category";
  elements.override.textContent = snapshot.override_count;
  elements.budget.textContent = formatBudget(snapshot.price_preference);

  elements.constraintCount.textContent = snapshot.explicit_constraints.length;
  elements.constraintList.replaceChildren();
  if (!snapshot.explicit_constraints.length) {
    elements.constraintList.innerHTML = '<span class="empty-state">Nothing stated yet</span>';
  } else {
    snapshot.explicit_constraints.forEach((constraint) => {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = constraint;
      elements.constraintList.append(tag);
    });
  }

  elements.needCount.textContent = snapshot.hidden_need_hypotheses.length;
  elements.needList.replaceChildren();
  if (!snapshot.hidden_need_hypotheses.length) {
    elements.needList.innerHTML = '<span class="empty-state">Context will appear here</span>';
  } else {
    snapshot.hidden_need_hypotheses.forEach((need) => {
      const item = document.createElement("div");
      item.className = "need-item";
      const value = document.createElement("strong");
      value.textContent = need.value;
      const evidence = document.createElement("span");
      evidence.textContent = `${Math.round(need.confidence * 100)}% · ${need.evidence}`;
      item.append(value, evidence);
      elements.needList.append(item);
    });
  }
}

function formatBudget(budget) {
  if (!budget) return "Not set";
  if (budget.target) return `Around $${budget.target}`;
  if (budget.minimum && budget.maximum) return `$${budget.minimum}–$${budget.maximum}`;
  if (budget.maximum) return `Under $${budget.maximum}`;
  if (budget.minimum) return `Over $${budget.minimum}`;
  return "Not set";
}

function renderRecommendations(items) {
  elements.recommendations.replaceChildren();
  elements.resultCount.textContent = `${items.length} product${items.length === 1 ? "" : "s"}`;
  items.forEach((product, index) => {
    const card = document.createElement("article");
    card.className = "product-card";
    card.style.animationDelay = `${index * 70}ms`;
    const evidence = product.evidence.length
      ? `<div class="evidence">${product.evidence.map((term) => `<span>${escapeHtml(term)}</span>`).join("")}</div>`
      : "";
    card.innerHTML = `
      <div class="product-topline">
        <span class="rank">0${product.rank}</span>
        <span class="price">${escapeHtml(product.price)}</span>
      </div>
      <h3>${escapeHtml(product.title)}</h3>
      <p class="store">${escapeHtml(product.store)}</p>
      <div class="product-meta">
        <span class="rating">★ ${product.average_rating.toFixed(1)}</span>
        <span>${product.rating_number.toLocaleString()} ratings</span>
        <span>${escapeHtml(product.parent_asin)}</span>
      </div>
      ${evidence}`;
    elements.recommendations.append(card);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function sendMessage(message) {
  if (!message.trim() || state.busy) return;
  state.busy = true;
  elements.sendButton.disabled = true;
  addMessage("user", message);
  const loading = addMessage("agent", "", true);
  try {
    state.turn += 1;
    const result = await api("/api/chat", {
      session_id: state.sessionId,
      message,
      turn: state.turn,
      top_k: 3,
    });
    loading.remove();
    addMessage("agent", result.message);
    renderState(result.state);
    renderRecommendations(result.recommendations);
    elements.turn.textContent = `Turn ${state.turn}`;
  } catch (error) {
    loading.remove();
    addMessage("agent", `I couldn't process that request: ${error.message}`);
  } finally {
    state.busy = false;
    elements.sendButton.disabled = false;
  }
}

async function resetConversation() {
  state.sessionId = `web-${Date.now()}`;
  state.turn = 0;
  elements.turn.textContent = "Turn 0";
  elements.messages.replaceChildren();
  elements.recommendations.innerHTML = `
    <div class="results-empty">
      <span>01</span><h3>Ready when you are</h3>
      <p>Recommendations will update as the conversation becomes clearer.</p>
    </div>`;
  elements.resultCount.textContent = "0 products";
  const result = await api("/api/reset", { session_id: state.sessionId });
  renderState(result.state);
}

async function playScenario(name) {
  await resetConversation();
  document.querySelectorAll(".scenario-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.scenario === name);
  });
  for (const message of scenarios[name]) {
    await sendMessage(message);
  }
}

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = elements.input.value;
  elements.input.value = "";
  await sendMessage(message);
});
elements.resetButton.addEventListener("click", resetConversation);
document.querySelectorAll(".scenario-button").forEach((button) => {
  button.addEventListener("click", () => playScenario(button.dataset.scenario));
});

playScenario("retreat");
