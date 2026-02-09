"use client";

import { useState } from "react";
import { useProject } from "@/components/ProjectProvider";
import { runBNWFAnalysis } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

const COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"];

export default function FEMAnalysis() {
  const { project, update } = useProject();
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!project.soil_layers.length) { alert("Define soil layers first."); return; }
    setLoading(true);
    try {
      const res = await runBNWFAnalysis(project);
      setResult(res);
    } catch (e: any) {
      alert(e.message);
    }
    setLoading(false);
  };

  // Chart data builders
  const lateralDefl = result ? result.depth_ft.map((d: number, i: number) => ({
    depth: -d, value: result.deflection_lateral_in[i],
  })) : [];

  const axialDefl = result ? result.depth_ft.map((d: number, i: number) => ({
    depth: -d, value: result.deflection_axial_in[i],
  })) : [];

  const momentData = result ? result.depth_ft.map((d: number, i: number) => ({
    depth: -d, value: result.moment_ft_lbs[i],
  })) : [];

  const shearData = result ? result.depth_ft.map((d: number, i: number) => ({
    depth: -d, value: result.shear_lbs[i],
  })) : [];

  const axialForceData = result ? result.depth_ft.map((d: number, i: number) => ({
    depth: -d, value: result.axial_force_lbs[i],
  })) : [];

  const soilReaction = result ? result.depth_ft.map((d: number, i: number) => ({
    depth: -d, value: result.soil_reaction_p_lb_in[i],
  })) : [];

  const pushoverData = result?.pushover_load ? result.pushover_load.map((l: number, i: number) => ({
    disp: result.pushover_disp[i], load: l,
  })) : [];

  const tzData = result?.tz_curves?.map((tz: any) => ({
    label: `z=${tz.depth_ft.toFixed(0)} ft`,
    data: tz.z.map((z: number, i: number) => ({ z, t: tz.t[i] })),
  })) || [];

  const qzData = result?.qz_curve ? result.qz_curve.z.map((z: number, i: number) => ({
    z, q: result.qz_curve.q[i],
  })) : [];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">FEM / BNWF Analysis</h2>

      {/* Configuration */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <div>
          <label className="block text-sm mb-1">Analysis Type</label>
          <select className="w-full border rounded px-3 py-2" value={project.bnwf_analysis_type}
            onChange={(e) => update({ bnwf_analysis_type: e.target.value })}>
            <option value="static">Static (Combined)</option>
            <option value="pushover_lateral">Pushover — Lateral</option>
            <option value="pushover_axial">Pushover — Axial</option>
          </select>
        </div>
        <div>
          <label className="block text-sm mb-1">V_axial (lbs)</label>
          <input type="number" className="w-full border rounded px-3 py-2"
            value={project.dead} step={100}
            onChange={(e) => update({ dead: parseFloat(e.target.value) || 0 })} />
        </div>
        <div>
          <label className="block text-sm mb-1">H_lateral (lbs)</label>
          <input type="number" className="w-full border rounded px-3 py-2"
            value={project.wind_lateral} step={100}
            onChange={(e) => update({ wind_lateral: parseFloat(e.target.value) || 0 })} />
        </div>
        <div>
          <label className="block text-sm mb-1">M_ground (ft-lbs)</label>
          <p className="border rounded px-3 py-2 bg-gray-50">
            {(project.wind_lateral * project.lever_arm).toLocaleString()}
          </p>
        </div>
      </div>

      <div className="flex gap-4 items-center mb-6">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={project.bnwf_include_p_delta}
            onChange={(e) => update({ bnwf_include_p_delta: e.target.checked })} />
          P-Delta
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={project.cyclic}
            onChange={(e) => update({ cyclic: e.target.checked })} />
          Cyclic
        </label>
        {project.bnwf_analysis_type.startsWith("pushover") && (
          <>
            <div>
              <label className="block text-xs mb-1">Steps</label>
              <input type="number" className="border rounded px-2 py-1 w-20"
                value={project.bnwf_pushover_steps} min={5} max={50}
                onChange={(e) => update({ bnwf_pushover_steps: parseInt(e.target.value) || 20 })} />
            </div>
            <div>
              <label className="block text-xs mb-1">Max multiplier</label>
              <input type="number" className="border rounded px-2 py-1 w-20"
                value={project.bnwf_pushover_max_mult} step={0.5}
                onChange={(e) => update({ bnwf_pushover_max_mult: parseFloat(e.target.value) || 3.0 })} />
            </div>
          </>
        )}
        <button onClick={run} disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 ml-auto">
          {loading ? "Solving..." : "Run BNWF Analysis"}
        </button>
      </div>

      {result && (
        <>
          {/* Solver info */}
          <div className="text-sm text-gray-500 mb-2">
            Solver: {result.solver_used} | {result.converged
              ? `Converged in ${result.iterations} iterations`
              : `Did not converge after ${result.iterations} iterations`}
          </div>

          {/* Key metrics */}
          <div className="grid grid-cols-5 gap-3 mb-6">
            <Metric label="Lateral Deflection" value={`${result.y_ground_lateral.toFixed(3)} in`} />
            <Metric label="Axial Settlement" value={`${result.y_ground_axial.toFixed(4)} in`} />
            <Metric label="Max Moment" value={`${Math.round(result.M_max).toLocaleString()} ft-lbs`} />
            <Metric label="Depth of M_max" value={`${result.depth_M_max.toFixed(1)} ft`} />
            {result.P_critical && (
              <Metric label="P_critical (buckling)" value={`${Math.round(result.P_critical).toLocaleString()} lbs`} />
            )}
          </div>

          {/* Stiffness matrix */}
          <div className="bg-white border rounded p-4 mb-6">
            <h3 className="font-semibold mb-2">Pile Head Stiffness Matrix (K_head)</h3>
            <table className="text-sm">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-4 py-1"></th>
                  <th className="px-4 py-1">Axial (lb/in)</th>
                  <th className="px-4 py-1">Lateral (lb/in)</th>
                  <th className="px-4 py-1">Rotational (lb/rad)</th>
                </tr>
              </thead>
              <tbody>
                {["Axial", "Lateral", "Rotational"].map((label, r) => (
                  <tr key={r} className="border-t">
                    <td className="px-4 py-1 font-medium">{label}</td>
                    {[0, 1, 2].map((c) => (
                      <td key={c} className="px-4 py-1 text-right font-mono">
                        {result.K_head[r]?.[c]?.toExponential(2) ?? "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Depth profiles (6 charts) */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <ChartPanel title="Lateral Deflection (in)" data={lateralDefl} color="#3498db" xKey="value" />
            <ChartPanel title="Axial Displacement (in)" data={axialDefl} color="#1abc9c" xKey="value" />
            <ChartPanel title="Moment (ft-lbs)" data={momentData} color="#e74c3c" xKey="value" />
            <ChartPanel title="Shear (lbs)" data={shearData} color="#2ecc71" xKey="value" />
            <ChartPanel title="Axial Force (lbs)" data={axialForceData} color="#9b59b6" xKey="value" />
            <ChartPanel title="Lateral Soil Reaction (lb/in)" data={soilReaction} color="#f39c12" xKey="value" />
          </div>

          {/* Pushover curve */}
          {pushoverData.length > 0 && (
            <div className="bg-white border rounded p-4 mb-6">
              <h3 className="font-semibold mb-3">Pushover Curve ({result.pushover_axis})</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={pushoverData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="disp" label={{ value: "Displacement (in)", position: "bottom" }} />
                  <YAxis label={{ value: "Load (lbs)", angle: -90 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="load" stroke="#e74c3c" strokeWidth={2} dot />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* t-z curves */}
          {tzData.length > 0 && (
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-white border rounded p-4">
                <h3 className="font-semibold mb-3">t-z Curves (Skin Friction Transfer)</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="z" type="number" label={{ value: "z (in)", position: "bottom" }} />
                    <YAxis label={{ value: "t (lb/in)", angle: -90 }} />
                    <Tooltip />
                    {tzData.map((curve: any, i: number) => (
                      <Line key={i} data={curve.data} dataKey="t" name={curve.label}
                        stroke={COLORS[i % 5]} dot={false} strokeWidth={2} type="monotone" />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
              {qzData.length > 0 && (
                <div className="bg-white border rounded p-4">
                  <h3 className="font-semibold mb-3">q-z Curve (Tip Resistance)</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={qzData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="z" label={{ value: "z (in)", position: "bottom" }} />
                      <YAxis label={{ value: "Q (lbs)", angle: -90 }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="q" stroke="#e67e22" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          )}

          {/* Notes */}
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

function ChartPanel({ title, data, color, xKey }: { title: string; data: any[]; color: string; xKey: string }) {
  return (
    <div className="bg-white border rounded p-4">
      <h3 className="font-semibold mb-2 text-sm">{title}</h3>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} type="number" tick={{ fontSize: 10 }} />
          <YAxis dataKey="depth" tick={{ fontSize: 10 }} />
          <Tooltip />
          <Line type="monotone" dataKey={xKey} stroke={color} dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
