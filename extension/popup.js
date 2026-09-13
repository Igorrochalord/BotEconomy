const statusEl = document.getElementById("status");

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.style.color = isError ? "#b91c1c" : "#64748b";
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`tab-${tab.dataset.tab}`).classList.add("active");
  });
});

document.getElementById("open-options").addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

document.getElementById("refresh").addEventListener("click", loadAll);

async function loadAll() {
  setStatus("Atualizando...");
  try {
    const { apiBaseUrl } = await getSettings();
    if (!apiBaseUrl) {
      setStatus("Configure a URL do backend em Configurações.", true);
      return;
    }
    await Promise.all([loadMovers(), loadTickers(), loadAlerts()]);
    setStatus(`Conectado a ${apiBaseUrl}`);
  } catch (err) {
    setStatus(err.message || "Falha ao conectar ao backend.", true);
  }
}

function renderMoversList(el, entries) {
  el.innerHTML = "";
  for (const [ticker, value] of entries) {
    const li = document.createElement("li");
    const cls = value >= 0 ? "positive" : "negative";
    li.innerHTML = `<span>${ticker}</span><span class="${cls}">${value.toFixed(2)}%</span>`;
    el.appendChild(li);
  }
}

async function loadMovers() {
  const data = await apiFetch("/api/summary");
  renderMoversList(document.getElementById("top-positive"), Object.entries(data.top_positive));
  renderMoversList(document.getElementById("top-negative"), Object.entries(data.top_negative));
}

async function loadTickers() {
  const data = await apiFetch("/api/tickers");
  const el = document.getElementById("tickers-list");
  el.innerHTML = "";
  for (const ticker of data.tickers) {
    const li = document.createElement("li");
    li.innerHTML = `<span>${ticker}</span>`;
    const removeBtn = document.createElement("button");
    removeBtn.textContent = "remover";
    removeBtn.addEventListener("click", async () => {
      try {
        await apiFetch(`/api/tickers/${ticker}`, { method: "DELETE" });
        await loadTickers();
      } catch (err) {
        setStatus(err.message, true);
      }
    });
    li.appendChild(removeBtn);
    el.appendChild(li);
  }
}

async function loadAlerts() {
  const data = await apiFetch("/api/alerts");
  const el = document.getElementById("alerts-list");
  el.innerHTML = "";
  for (const alert of data.alerts) {
    const li = document.createElement("li");
    const label = `${alert.ticker} ${alert.condition === "above" ? "≥" : "≤"} ${alert.price}${alert.triggered ? " ✅" : ""}`;
    li.innerHTML = `<span>${label}</span>`;
    const removeBtn = document.createElement("button");
    removeBtn.textContent = "remover";
    removeBtn.addEventListener("click", async () => {
      try {
        await apiFetch(`/api/alerts/${alert.id}`, { method: "DELETE" });
        await loadAlerts();
      } catch (err) {
        setStatus(err.message, true);
      }
    });
    li.appendChild(removeBtn);
    el.appendChild(li);
  }
}

document.getElementById("add-ticker-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("new-ticker");
  try {
    await apiFetch("/api/tickers", { method: "POST", body: JSON.stringify({ ticker: input.value }) });
    input.value = "";
    await loadTickers();
  } catch (err) {
    setStatus(err.message, true);
  }
});

document.getElementById("add-alert-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const ticker = document.getElementById("alert-ticker");
  const condition = document.getElementById("alert-condition");
  const price = document.getElementById("alert-price");
  try {
    await apiFetch("/api/alerts", {
      method: "POST",
      body: JSON.stringify({ ticker: ticker.value, condition: condition.value, price: parseFloat(price.value) }),
    });
    ticker.value = "";
    price.value = "";
    await loadAlerts();
  } catch (err) {
    setStatus(err.message, true);
  }
});

document.getElementById("report").addEventListener("click", async () => {
  const { apiBaseUrl } = await getSettings();
  if (!apiBaseUrl) {
    setStatus("Configure a URL do backend em Configurações.", true);
    return;
  }
  chrome.tabs.create({ url: `${apiBaseUrl}/api/report` });
});

loadAll();
