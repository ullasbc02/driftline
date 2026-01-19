import { useEffect, useState } from "react";
import { listDrifts } from "./api";

export default function DriftList({ onSelect }) {
  const [drifts, setDrifts] = useState([]);

  useEffect(() => {
    listDrifts("local").then(d => setDrifts(d.drift_ids));
  }, []);

  return (
    <div>
      <h2>Detected Drifts</h2>
      <ul>
        {drifts.map(id => (
          <li key={id}>
            <button onClick={() => onSelect(id)}>
              {id}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
