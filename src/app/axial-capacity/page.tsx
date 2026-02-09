"use client";

import { useState } from "react";
import { useProject } from "@/components/ProjectProvider";
import { runAxialAnalysis } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function AxialCapacity() {
  const { project, update } = useProject();
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!project.soil_layers.length) { alert("Define soil layers first."); return; }
    setLoading(true);
    try {
      const res = await runAxialAnalysis(project);
      setResult(res);
    } catch (e: any) {
      alert(e.message);
    }
    setLoading(false);
  };

  const barData = result ? [
    { name: "Comp\nUltimate", value: Math.round(result.Q_ult_compression), fill: "#2ecc71" },
    { name: "Comp\nAllowable", value: Math.round(result.Q_allow_compression), fill: "#27ae60" },
    { name: "Comp\nLRFD", value: Math.round(result.Q_r_compression), fill: "#1abc9c" },
    { name: "Tens\nUltimate", value: Math.round(result.Q_ult_tension), fill: "#e74c3c" },
    { name: "Tens\nAllowable", value: Math.round(result.Q_allow_tension), fill: "#c0392b" },
    { name: "Tens\nLRFD", value: Math.round(result.Q_r_tension), fill: "#e67e22" },
  ] : [];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Axial Capacity Analysis</h2>

      <div className="flex gap-4 items-end mb-6">
        <div>
          <label className="block text-sm mb-1">Method</label>
          <select className="border rounded px-3 py-2" value={project.axial_method}
            onChange={(e) => update({ axial_method: e.target.value })}>
            <option value="auto">Auto</option>
            <option value="alpha">Alpha (Clay)</option>
            <option value="beta">Beta (Effective Stress)</option>
            <option value="meyerhof">Meyerhof SPT</option>
          </select>
        </div>
        <div>
          <label className="block text-sm mb-1">FS Compression</label>
          <input type="number" className="border rounded px-3 py-2 w-24"
            value={project.FS_compression} step={0.5}
            onChange={(e) => update({ FS_compression: parseFloat(e.target.value) })} />
        </div>
        <div>
          <label className="block text-sm mb-1">FS Tension</label>
          <input type="number" className="border rounded px-3 py-2 w-24"
            value={project.FS_tension} step={0.5}
            onChange={(e) => update({ FS_tension: parseFloat(e.target.value) })} />
        </div>
        <button onClick={run} disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
          {loading ? "Running..." : "Run Analysis"}
        </button>
      </div>

      {result && (
        <>
          {/* Metrics */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <Metric label="Q_s (Skin Friction)" value={`${result.Q_s.toLocaleString()} lbs`} />
            <Metric label="Q_b (End Bearing)" value={`${result.Q_b.toLocaleString()} lbs`} />
            <Metric label="Q_ult Compression" value={`${result.Q_ult_compression.toLocaleString()} lbs`} />
            <Metric label="Q_allow Compression (ASD)" value={`${Math.round(result.Q_allow_compression).toLocaleString()} lbs`} />
            <Metric label="Q_ult Tension" value={`${Math.round(result.Q_ult_tension).toLocaleString()} lbs`} />
            <Metric label="Q_allow Tension (ASD)" value={`${Math.round(result.Q_allow_tension).toLocaleString()} lbs`} />
          </div>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <Metric label={`LRFD phi*Rn Comp (phi=${result.phi_compression})`}
              value={`${Math.round(result.Q_r_compression).toLocaleString()} lbs`} />
            <Metric label={`LRFD phi*Rn Tens (phi=${result.phi_tension})`}
              value={`${Math.round(result.Q_r_tension).toLocaleString()} lbs`} />
          </div>

          {/* Chart */}
          <div className="bg-white border rounded p-4 mb-6">
            <h3 className="font-semibold mb-3">Capacity Summary</h3>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(v: number) => `${v.toLocaleString()} lbs`} />
                <Bar dataKey="value" fill="#3498db" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Layer table */}
          {result.layer_contributions?.length > 0 && (
            <div className="bg-white border rounded overflow-hidden mb-6">
              <h3 className="font-semibold p-3">Layer-by-Layer Breakdown</h3>
              <table className="w-full text-sm">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-3 py-2 text-left">Depth (ft)</th>
                    <th className="px-3 py-2 text-left">Layer</th>
                    <th className="px-3 py-2 text-left">Method</th>
                    <th className="px-3 py-2 text-right">f_s (psf)</th>
                    <th className="px-3 py-2 text-right">dQ (lbs)</th>
                  </tr>
                </thead>
                <tbody>
                  {result.layer_contributions.map((lc: any, i: number) => (
                    <tr key={i} className="border-t">
                      <td className="px-3 py-2">{lc.depth_ft}</td>
                      <td className="px-3 py-2">{lc.layer}</td>
                      <td className="px-3 py-2">{lc.method}</td>
                      <td className="px-3 py-2 text-right">{lc.f_s_psf}</td>
                      <td className="px-3 py-2 text-right">{Math.round(lc.dQ_lbs).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Notes */}
          <div className="bg-gray-50 rounded p-4">
            <h3 className="font-semibold mb-2">Notes</h3>
            <ul className="text-sm space-y-1">
              {result.notes.map((n: string, i: number) => <li key={i}>- {n}</li>)}
            </ul>
          </div>
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
