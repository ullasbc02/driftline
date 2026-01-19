import { useState } from "react";
import DriftList from "./DriftList";
import DriftDetail from "./DriftDetail";

export default function App() {
  const [selected, setSelected] = useState(null);

  return (
    <div style={{ display: "flex", gap: "40px" }}>
      <DriftList onSelect={setSelected} />
      {selected && <DriftDetail driftId={selected} />}
    </div>
  );
}
