import { useEffect, useState } from "react";
import { getDrift, getEvidence, getIncidentReport, runIncidentAgent } from "./api";

export default function DriftDetail({ driftId }) {
  const [drift, setDrift] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [incident, setIncident] = useState(null);
  const [agentStatus, setAgentStatus] = useState("idle");
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!driftId) return;
    setDrift(null);
    setEvidence(null);
    setIncident(null);
    setError(null);
    setAgentStatus("idle");

    getDrift(driftId).then(setDrift).catch(err => setError(err.message));
    getEvidence(driftId)
      .then(setEvidence)
      .catch(() => setEvidence({ unavailable: true }));
    getIncidentReport(driftId).then(setIncident).catch(() => setIncident(null));
  }, [driftId]);

  async function handleRunAgent() {
    setAgentStatus("running");
    setError(null);
    try {
      const report = await runIncidentAgent(driftId);
      setIncident(report);
      setAgentStatus("complete");
    } catch (err) {
      setError(err.message);
      setAgentStatus("idle");
    }
  }

  if (!drift || !evidence) return <div className="panel">Loading...</div>;

  return (
    <div className="detail">
      <div className="detailHeader">
        <div>
          <h2>Drift Summary</h2>
          <p className="muted">{drift.id}</p>
        </div>
        <button
          className="primaryButton"
          onClick={handleRunAgent}
          disabled={agentStatus === "running"}
        >
          {agentStatus === "running" ? "Investigating..." : "Run Incident Agent"}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      <p>{drift.summary}</p>

      <div className="findingGrid">
        {drift.findings.map((finding, index) => (
          <div className="finding" key={`${finding.subject}-${index}`}>
            <span>{finding.drift_type.replace("_", " ")}</span>
            <strong>{finding.severity}</strong>
            <p>{finding.subject}</p>
          </div>
        ))}
      </div>

      {incident && (
        <section className="agentResult">
          <div className="sectionTitle">
            <h3>Incident Commander</h3>
            <span>{incident.decision.action.replace("_", " ")}</span>
          </div>
          <div className="commanderGrid">
            <div>
              <label>Root Cause</label>
              <p>{incident.root_cause}</p>
            </div>
            <div>
              <label>Confidence</label>
              <p>{Math.round(incident.confidence * 100)}%</p>
            </div>
            <div>
              <label>Recommended Action</label>
              <p>{incident.decision.recommendation}</p>
            </div>
            <div>
              <label>Slack</label>
              <p>{incident.slack.status} / {incident.slack.channel}</p>
            </div>
          </div>

          <h3>Slack Notification</h3>
          <pre>{incident.slack.message}</pre>

          <h3>Incident Report</h3>
          <pre>{incident.report_markdown}</pre>
        </section>
      )}

      <h3>Metrics</h3>
      <pre>{JSON.stringify({
        baseline: evidence.baseline_metrics,
        current: evidence.current_metrics
      }, null, 2)}</pre>

      <h3>Graph Diff</h3>
      <pre>{JSON.stringify(evidence.graph_diff, null, 2)}</pre>

      <h3>Trace Evidence</h3>
      <pre>{JSON.stringify(evidence.trace_samples, null, 2)}</pre>

      <h3>Explanation</h3>
      <p>{evidence.explanation || "No persisted evidence pack was found; agent used drift findings directly."}</p>
    </div>
  );
}
