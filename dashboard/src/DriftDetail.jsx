import { useEffect, useState } from "react";
import { getDrift, getEvidence } from "./api";

export default function DriftDetail({ driftId }) {
  const [drift, setDrift] = useState(null);
  const [evidence, setEvidence] = useState(null);

  useEffect(() => {
    if (!driftId) return;
    getDrift(driftId).then(setDrift);
    getEvidence(driftId).then(setEvidence);
  }, [driftId]);

  if (!drift || !evidence) return <div>Loading...</div>;

  return (
    <div>
      <h3>Drift Summary</h3>
      <p>{drift.summary}</p>

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
      <p>{evidence.explanation}</p>
    </div>
  );
}
