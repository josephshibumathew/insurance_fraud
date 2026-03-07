const STORAGE_KEY = "claim_extended_fields";

function readStore() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (_error) {
    return {};
  }
}

function writeStore(store) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

export function saveClaimExtendedFields(claimId, payload) {
  const store = readStore();
  store[String(claimId)] = payload;
  writeStore(store);
}

export function getClaimExtendedFields(claimId) {
  const store = readStore();
  return store[String(claimId)] || null;
}
