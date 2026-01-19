const BASE = "http://localhost:9000";

export async function listDrifts(env) {
  const res = await fetch(`${BASE}/drift/list?env=${env}`);
  return res.json();
}

export async function getDrift(driftId) {
  const res = await fetch(`${BASE}/drift/get?drift_id=${driftId}`);
  return res.json();
}

export async function getEvidence(driftId) {
  const res = await fetch(`${BASE}/evidence/get?drift_event_id=${driftId}`);
  return res.json();
}
