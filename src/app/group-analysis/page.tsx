"use client";

import { useState } from "react";
import { useProject } from "@/components/ProjectProvider";
import { runGroupAnalysis } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";

export default function GroupAnalysis() {
  const { project, update } = useProject();
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [qSingle, setQSingle] = useState(10000);

  const run = async () => {
    if (!project.soil_layers.length) { alert("Define soil layers first."); return; }
    if (project.group_n_rows * project.group_n_cols <= 1) { alert("Need at least 2 piles for group analysis."); return; }
    setLoading(true);
    try {
      const res = await runGroupAnalysis(project, qSingle);
      setResult(res);
    } catch (e: any) {
      alert(e.message);
    }
    setLoading(false);
  };

  const pmData = result?.p_multipliers?.map((r: any) => ({
    name: `Row ${r.row}\n(${r.position})`,
    f_m: r.f_m,
  })) || [];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Pile Group Analysis</h2>

      <div className="grid grid-cols-4 gap-4 mb-6 max-w-3xl">
        <div>
          <label className="block text-sm mb-1">Rows</label>
          <input type="number" className="w-full border rounded px-3 py-2"
            value={project.group_n_rows} min={1} max={10}
            onChange={(e) => update({ group_n_rows: parseInt(e.target.value) || 1 })} />
        </div>
        <div>
          <label className="block text-sm mb-1">Piles per Row</label>
          <input type="number" className="w-full border rounded px-3 py-2"
            value={project.group_n_cols} min={1} max={10}
            onChange={(e) => update({ group_n_cols: parseInt(e.target.value) || 1 })} />
        </div>
        <div>
          <label className="block text-sm mb-1">Spacing (in)</label>
          <input type="number" className="w-full border rounded px-3 py-2"
            value={project.group_spacing} min={6} step={3}
            onChange={(e) => update({ group_spacing: parseFloat(e.target.value) || 36 })} />
        </div>
        <div>
          <label className="block text-sm mb-1">Q_single (lbs)</label>
          <input type="number" className="w-full border rounded px-3 py-2"
            value={qSingle} step={1000}
            onChange={(e) => setQSingle(parseFloat(e.target.value) || 10000)} />
        </div>
      </div>

      <div className="flex gap-4 mb-2">
        <p className="text-sm text-gray-600">Total piles: {project.group_n_rows * project.group_n_cols}</p>
        <p className="text-sm text-gray-600">Spacing: {(project.group_spacing / 12).toFixed(1)} ft</p>
      </div>

      <button onClick={run} disabled={loading}
        className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 mb-6">
        {loading ? "Running..." : "Run Group Analysis"}
      </button>

      {result && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <Metric label="Converse-Labarre eta" value={result.eta_axial.toString()} />
            <Metric label="Group Capacity (individual)" value={`${Math.round(result.Q_group_individual).toLocaleString()} lbs`} />
            <Metric label={result.Q_block ? "Block Failure Capacity" : "Block Failure"}
              value={result.Q_block ? `${Math.round(result.Q_block).toLocaleString()} lbs` : "N/A"} />
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-6">
            <p className="font-semibold">Governing Group Capacity: {Math.round(result.Q_group_governing).toLocaleString()} lbs</p>
          </div>

          <div className="grid grid-cols-2 gap-6 mb-6">
            {/* p-multipliers */}
            <div className="bg-white border rounded p-4">
              <h3 className="font-semibold mb-3">p-Multipliers by Row</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={pmData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 1.1]} />
                  <Tooltip />
                  <ReferenceLine y={1} stroke="#999" strokeDasharray="3 3" label="No reduction" />
                  <Bar dataKey="f_m" fill="#3498db" />
                </BarChart>
              </ResponsiveContainer>
              <p className="text-sm mt-2">Average lateral efficiency: <strong>{result.eta_lateral}</strong></p>
            </div>

            {/* p-multiplier table */}
            <div className="bg-white border rounded p-4">
              <h3 className="font-semibold mb-3">p-Multiplier Table</h3>
              <table className="w-full text-sm">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-3 py-2 text-left">Row</th>
                    <th className="px-3 py-2 text-left">Position</th>
                    <th className="px-3 py-2 text-right">f_m</th>
                  </tr>
                </thead>
                <tbody>
                  {result.p_multipliers.map((r: any, i: number) => (
                    <tr key={i} className="border-t">
                      <td className="px-3 py-2">{r.row}</td>
                      <td className="px-3 py-2">{r.position}</td>
                      <td className="px-3 py-2 text-right">{r.f_m.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Group layout */}
          <div className="bg-white border rounded p-4 mb-6">
            <h3 className="font-semibold mb-3">Group Layout (Plan View)</h3>
            <div className="relative" style={{ height: Math.max(200, project.group_n_rows * 60 + 40) }}>
              {Array.from({ length: project.group_n_rows }, (_, r) =>
                Array.from({ length: project.group_n_cols }, (_, c) => (
                  <div key={`${r}-${c}`}
                    className="absolute w-8 h-8 bg-blue-500 rounded flex items-center justify-center text-white text-xs"
                    style={{ left: c * 60 + 40, top: r * 60 + 20 }}>
                    {r + 1},{c + 1}
                  </div>
                ))
              )}
              <div className="absolute text-red-500 text-xs font-bold" style={{ left: 0, top: project.group_n_rows * 30 }}>
                &rarr; Load
              </div>
            </div>
          </div>

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
