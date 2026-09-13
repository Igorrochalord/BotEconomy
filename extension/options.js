const apiBaseUrlInput = document.getElementById("apiBaseUrl");
const apiKeyInput = document.getElementById("apiKey");
const refreshMinutesInput = document.getElementById("refreshMinutes");
const savedLabel = document.getElementById("saved");

async function load() {
  const { apiBaseUrl, apiKey, refreshMinutes } = await getSettings();
  apiBaseUrlInput.value = apiBaseUrl;
  apiKeyInput.value = apiKey;
  refreshMinutesInput.value = refreshMinutes;
}

document.getElementById("save").addEventListener("click", async () => {
  const apiBaseUrl = apiBaseUrlInput.value.trim().replace(/\/$/, "");
  const apiKey = apiKeyInput.value.trim();
  const refreshMinutes = Math.max(5, parseInt(refreshMinutesInput.value, 10) || 15);

  if (apiBaseUrl) {
    // Manifest V3 requires explicit runtime consent for host permissions
    // that weren't declared statically — we only know the backend's origin
    // once the user types it here, so we ask for it at save time.
    const origin = `${new URL(apiBaseUrl).origin}/*`;
    const granted = await chrome.permissions.request({ origins: [origin] });
    if (!granted) {
      savedLabel.textContent = "Permissão negada — a extensão não pode acessar essa URL.";
      savedLabel.style.color = "#b91c1c";
      return;
    }
  }

  await saveSettings({ apiBaseUrl, apiKey, refreshMinutes });
  chrome.runtime.sendMessage({ type: "reschedule", refreshMinutes });

  savedLabel.textContent = "Salvo!";
  savedLabel.style.color = "#15803d";
  setTimeout(() => (savedLabel.textContent = ""), 2000);
});

load();
