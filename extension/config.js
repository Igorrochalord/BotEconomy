// Shared helpers for reading/writing the extension's connection settings.
// Kept dependency-free (no bundler) so the extension can be loaded unpacked.

const DEFAULTS = {
  apiBaseUrl: "http://localhost:8000",
  apiKey: "",
  refreshMinutes: 15,
};

async function getSettings() {
  const stored = await chrome.storage.sync.get(DEFAULTS);
  return { ...DEFAULTS, ...stored };
}

async function saveSettings(partial) {
  await chrome.storage.sync.set(partial);
}

async function apiFetch(path, options = {}) {
  const { apiBaseUrl, apiKey } = await getSettings();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (apiKey) headers["X-API-Key"] = apiKey;

  const response = await fetch(`${apiBaseUrl}${path}`, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || `Erro ${response.status}`);
  }
  return body;
}
