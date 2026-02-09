"use client";

import { useState } from "react";
import { useProject } from "@/components/ProjectProvider";
import { runLateralAnalysis } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function LateralAnalysis() {
  const { project, update } = useProject();
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!project.soil_layers.length) { alert("Define soil layers first."); return; }
    setLoading(true);
    try {
      const res = await runLateralAnalysis(project);
      setResult(res);
    } catch (e: any) {
      alert(e.message);
    }
    setLoading(false);
  };

  // Build chart data from arrays
  const deflData = result ? result.depth_ft.map((d: number, i: number) => ({
    depth: -d, deflection: result.deflection_in[i],
  })) : [];

  const momentData = result ? result.depth_ft.map((d: number, i: number) => ({
    depth: -d, moment: result.moment_ft_lbs[i],
  })) : [];

  const pyData = result?.py_curves?.map((py: any) => ({
    label: `z=${py.depth_ft.toFixed(0)} ft`,
    data: py.y.map((y: number, i: number) => ({ y, p: py.p[i] })),
  })) || [];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Lateral Load Analysis</h2>

      <div className="flex gap-4 items-end mb-6">
        <div>
          <label className="block text-sm mb-1">Lateral Load H (lbs)</label>
          <input type="number" className="border rounded px-3 py-2 w-36"
            value={project.wind_lateral} step={100}
            onChange={(e) => update({ wind_lateral: parseFloat(e.target.value) })} />
        </div>
        <div>
          <label className="block text-sm mb-1">Load height (ft)</label>
          <input type="number" className="border rounded px-3 py-2 w-24"
            value={project.lever_arm} step={0.5}
            onChange={(e) => update({ lever_arm: parseFloat(e.target.value) })} />
        </div>
        <div>
          <label className="block text-sm mb-1">M_ground (ft-lbs)</label>
          <p className="border rounded px-3 py-2 bg-gray-50 w-36">
            {(project.wind_lateral * project.lever_arm).toLocaleString()}
          </p>
        </div>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={project.cyclic}
            onChange={(e) => update({ cyclic: e.target.checked })} />
          Cyclic
        </label>
        <button onClick={run} disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
          {loading ? "Solving..." : "Run Analysis"}
        </button>
      </div>

      {result && (
        <>
          {/* Key metrics */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <Metric label="Ground Deflection" value={`${result.y_ground.toFixed(3)} in`} />
            <Metric label="Max Moment" value={`${Math.round(result.M_max).toLocaleString()} ft-lbs`} />
            <Metric label="Depth of M_max" value={`${result.depth_M_max.toFixed(1)} ft`} />
            <Metric label="Depth Zero Deflection" value={`${result.depth_zero_defl.toFixed(1)} ft`} />
          </div>

          {/* DCR check */}
          <div className={`p-3 rounded mb-6 ${result.dcr <= 1 ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"}`}>
            <span className="font-semibold">
              Structural DCR = {result.dcr.toFixed(2)}
            </span>
            {" "}(M_max / M_y = {Math.abs(Math.round(result.M_max)).toLocaleString()} / {Math.round(result.My_ft_lbs).toLocaleString()} ft-lbs)
            {result.dcr <= 1 ? " -- OK" : " -- EXCEEDS YIELD"}
          </div>

          {result.converged ? (
            <p className="text-green-600 text-sm mb-4">Converged in {result.iterations} iterations</p>
          ) : (
            <p className="text-orange-600 text-sm mb-4">Did not converge after {result.iterations} iterations</p>
          )}

          {/* Charts */}
          <div className="grid grid-cols-2 gap-6 mb-6">
            <div className="bg-white border rounded p-4">
              <h3 className="font-semibold mb-3">Deflection vs Depth</h3>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={deflData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="deflection" label={{ value: "in", position: "bottom" }} />
                  <YAxis dataKey="depth" label={{ value: "Depth (ft)", angle: -90 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="deflection" stroke="#3498db" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-white border rounded p-4">
              <h3 className="font-semibold mb-3">Moment vs Depth</h3>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={momentData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="moment" label={{ value: "ft-lbs", position: "bottom" }} />
                  <YAxis dataKey="depth" label={{ value: "Depth (ft)", angle: -90 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="moment" stroke="#e74c3c" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* p-y curves */}
          {pyData.length > 0 && (
            <div className="bg-white border rounded p-4 mb-6">
              <h3 className="font-semibold mb-3">p-y Curves</h3>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="y" type="number" label={{ value: "y (in)", position: "bottom" }}
                    domain={["auto", "auto"]} />
                  <YAxis label={{ value: "p (lb/in)", angle: -90 }} />
                  <Tooltip />
                  {pyData.map((curve: any, i: number) => (
                    <Line key={i} data={curve.data} dataKey="p" name={curve.label}
                      stroke={["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"][i % 5]}
                      dot={false} strokeWidth={2} type="monotone" />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {result.notes?.length > 0 && (
            <div className="bg-gray-50 rounded p-4">
              <h3 className="font-semibold mb-2">Notes</h3>
              <ul className="text-sm space-y-1">
                {result.notes.map((n: string, i: number) => <li key={i}>- {n}</li>)}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border rounded p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-lg font-bold">{value}</p>
    </div>
  );
}
