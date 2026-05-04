import { useState } from "react";
import DriftList from "./DriftList";
import DriftDetail from "./DriftDetail";
import "./App.css";

export default function App() {
  const [selected, setSelected] = useState(null);

  return (
    <main className="appShell">
      <DriftList onSelect={setSelected} />
      <section className="workspace">
        {selected ? (
          <DriftDetail driftId={selected} />
        ) : (
          <div className="emptyState">
            <h1>Driftline</h1>
            <p>Select a drift event to inspect evidence and run the incident commander.</p>
          </div>
        )}
      </section>
    </main>
  );
}
