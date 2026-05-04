const BASE = "http://localhost:9000";

async function readJson(res) {
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = payload.detail || `Request failed with ${res.status}`;
    throw new Error(message);
  }
  return payload;
}

export async function listDrifts(env) {
  const res = await fetch(`${BASE}/drift/list?env=${env}`);
  return readJson(res);
}

export async function getDrift(driftId) {
  const res = await fetch(`${BASE}/drift/get?drift_id=${driftId}`);
  return readJson(res);
}

export async function getEvidence(driftId) {
  const res = await fetch(`${BASE}/evidence/get?drift_event_id=${driftId}`);
  return readJson(res);
}

export async function runIncidentAgent(driftId) {
  const res = await fetch(`${BASE}/agent/investigate/${driftId}`, {
    method: "POST",
  });
  return readJson(res);
}

export async function getIncidentReport(driftId) {
  const res = await fetch(`${BASE}/agent/report/${driftId}`);
  if (res.status === 404) return null;
  return readJson(res);
}
