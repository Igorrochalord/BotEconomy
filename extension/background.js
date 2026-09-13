importScripts("config.js");

const ALARM_NAME = "boteconomy-poll";

chrome.runtime.onInstalled.addListener(async () => {
  const { refreshMinutes } = await getSettings();
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: refreshMinutes });
  pollOnce();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) pollOnce();
});

// Options page calls this after the user changes the refresh interval.
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "reschedule") {
    chrome.alarms.create(ALARM_NAME, { periodInMinutes: message.refreshMinutes });
    sendResponse({ ok: true });
  }
});

async function pollOnce() {
  try {
    const [summary, alertsResp] = await Promise.all([
      apiFetch("/api/summary"),
      apiFetch("/api/alerts"),
    ]);
    await updateBadge(summary);
    await notifyNewlyTriggeredAlerts(alertsResp.alerts || []);
  } catch (err) {
    // Backend unreachable or not configured yet — badge shows a neutral
    // state instead of spamming notifications.
    chrome.action.setBadgeText({ text: "" });
    console.warn("BotEconomy: falha ao atualizar dados em segundo plano.", err);
  }
}

async function updateBadge(summary) {
  const values = Object.values(summary.top_positive || {});
  const best = values.length ? Math.max(...values) : null;
  if (best === null) {
    chrome.action.setBadgeText({ text: "" });
    return;
  }
  chrome.action.setBadgeBackgroundColor({ color: best >= 0 ? "#0f766e" : "#b91c1c" });
  chrome.action.setBadgeText({ text: `${best >= 0 ? "+" : ""}${best.toFixed(0)}%` });
}

async function notifyNewlyTriggeredAlerts(alerts) {
  const triggered = alerts.filter((a) => a.triggered);
  if (!triggered.length) return;

  const { seenAlertIds = [] } = await chrome.storage.local.get("seenAlertIds");
  const seen = new Set(seenAlertIds);
  const fresh = triggered.filter((a) => !seen.has(a.id));

  for (const alert of fresh) {
    chrome.notifications.create(`alert-${alert.id}`, {
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "BotEconomy — Alerta de preço",
      message: `${alert.ticker} atingiu ${alert.condition === "above" ? "acima de" : "abaixo de"} ${alert.price}`,
    });
    seen.add(alert.id);
  }
  await chrome.storage.local.set({ seenAlertIds: [...seen] });
}
