"use client";

import { useState } from "react";
import { useProject } from "@/components/ProjectProvider";
import { runLoadCombinations } from "@/lib/api";

export default function Loading() {
  const { project, update } = useProject();
  const [combos, setCombos] = useState<{ lrfd?: any[]; asd?: any[] } | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      const res = await runLoadCombinations(project);
      setCombos(res);
    } catch (e: any) {
      alert(e.message);
    }
    setLoading(false);
  };

  const numInput = (label: string, key: keyof typeof project, step = 100) => (
    <div>
      <label className="block text-xs mb-1">{label}</label>
      <input type="number" className="w-full border rounded px-2 py-1"
        value={project[key] as number} step={step}
        onChange={(e) => update({ [key]: parseFloat(e.target.value) || 0 })} />
    </div>
  );

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Loading</h2>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Design Method</label>
        <div className="flex gap-4">
          {["LRFD", "ASD", "Both"].map((m) => (
            <label key={m} className="flex items-center gap-1">
              <input type="radio" checked={project.design_method === m}
                onChange={() => update({ design_method: m })} />
              {m}
            </label>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6 max-w-4xl mb-6">
        <div className="space-y-3">
          <h3 className="font-semibold">Gravity Loads</h3>
          {numInput("Dead load (lbs)", "dead", 50)}
          {numInput("Live load (lbs)", "live", 50)}
          {numInput("Snow load (lbs)", "snow", 50)}
        </div>
        <div className="space-y-3">
          <h3 className="font-semibold">Wind Loads</h3>
          {numInput("Wind downward (lbs)", "wind_down")}
          {numInput("Wind uplift (lbs)", "wind_up")}
          {numInput("Wind lateral (lbs)", "wind_lateral")}
          {numInput("Wind moment (ft-lbs)", "wind_moment", 500)}
        </div>
        <div className="space-y-3">
          <h3 className="font-semibold">Seismic &amp; Geometry</h3>
          {numInput("Seismic lateral (lbs)", "seismic_lateral")}
          {numInput("Seismic vertical (lbs)", "seismic_vertical")}
          {numInput("Seismic moment (ft-lbs)", "seismic_moment", 500)}
          {numInput("Load height above ground (ft)", "lever_arm", 0.5)}
        </div>
      </div>

      <button onClick={run} disabled={loading}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
        {loading ? "Generating..." : "Generate Load Combinations"}
      </button>

      {combos && (
        <div className="mt-6 space-y-6">
          {combos.lrfd && (
            <div>
              <h3 className="font-semibold mb-2">LRFD Combinations</h3>
              <ComboTable rows={combos.lrfd} />
            </div>
          )}
          {combos.asd && (
            <div>
              <h3 className="font-semibold mb-2">ASD Combinations</h3>
              <ComboTable rows={combos.asd} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ComboTable({ rows }: { rows: any[] }) {
  return (
    <div className="bg-white border rounded overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-100">
          <tr>
            <th className="px-3 py-2 text-left">Load Case</th>
            <th className="px-3 py-2 text-right">V_comp (lbs)</th>
            <th className="px-3 py-2 text-right">V_tens (lbs)</th>
            <th className="px-3 py-2 text-right">H_lat (lbs)</th>
            <th className="px-3 py-2 text-right">M_ground (ft-lbs)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={`border-t ${r.name.includes("governs") || r.name.includes("UPLIFT") ? "bg-yellow-50 font-medium" : ""}`}>
              <td className="px-3 py-2">{r.name}</td>
              <td className="px-3 py-2 text-right">{Math.round(r.V_comp).toLocaleString()}</td>
              <td className="px-3 py-2 text-right">{Math.round(r.V_tens).toLocaleString()}</td>
              <td className="px-3 py-2 text-right">{Math.round(r.H_lat).toLocaleString()}</td>
              <td className="px-3 py-2 text-right">{Math.round(r.M_ground).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
