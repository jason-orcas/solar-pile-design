"use client";

import { useState } from "react";
import { useProject } from "@/components/ProjectProvider";
import { SOIL_TYPES, SoilLayerInput } from "@/lib/api";

export default function SoilProfile() {
  const { project, update } = useProject();
  const [form, setForm] = useState<SoilLayerInput>({
    top_depth: 0, thickness: 5, soil_type: "Sand", description: "",
    N_spt: 15, gamma: null, phi: null, c_u: null,
  });

  const addLayer = () => {
    update({ soil_layers: [...project.soil_layers, { ...form }] });
    setForm((f) => ({ ...f, top_depth: f.top_depth + f.thickness }));
  };

  const removeLayer = (i: number) => {
    update({ soil_layers: project.soil_layers.filter((_, idx) => idx !== i) });
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Soil Profile</h2>

      {/* Water table */}
      <div className="mb-6 flex items-center gap-4">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={project.water_table_depth !== null}
            onChange={(e) => update({ water_table_depth: e.target.checked ? 10 : null })}
          />
          Water table present
        </label>
        {project.water_table_depth !== null && (
          <input
            type="number"
            className="border rounded px-2 py-1 w-32"
            value={project.water_table_depth}
            step={0.5}
            onChange={(e) => update({ water_table_depth: parseFloat(e.target.value) })}
          />
        )}
        {project.water_table_depth !== null && <span className="text-sm text-gray-500">ft</span>}
      </div>

      {/* Add layer form */}
      <div className="bg-white border rounded p-4 mb-6">
        <h3 className="font-semibold mb-3">Add Layer</h3>
        <div className="grid grid-cols-4 gap-3">
          <div>
            <label className="block text-xs mb-1">Top Depth (ft)</label>
            <input type="number" className="w-full border rounded px-2 py-1" value={form.top_depth}
              step={0.5} onChange={(e) => setForm({ ...form, top_depth: parseFloat(e.target.value) })} />
          </div>
          <div>
            <label className="block text-xs mb-1">Thickness (ft)</label>
            <input type="number" className="w-full border rounded px-2 py-1" value={form.thickness}
              step={0.5} min={0.5} onChange={(e) => setForm({ ...form, thickness: parseFloat(e.target.value) })} />
          </div>
          <div>
            <label className="block text-xs mb-1">Soil Type</label>
            <select className="w-full border rounded px-2 py-1" value={form.soil_type}
              onChange={(e) => setForm({ ...form, soil_type: e.target.value })}>
              {SOIL_TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs mb-1">Description</label>
            <input type="text" className="w-full border rounded px-2 py-1" value={form.description || ""}
              placeholder="e.g., Brown silty sand"
              onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs mb-1">SPT N-value</label>
            <input type="number" className="w-full border rounded px-2 py-1" value={form.N_spt ?? ""}
              min={0} onChange={(e) => setForm({ ...form, N_spt: parseInt(e.target.value) || 0 })} />
          </div>
          <div>
            <label className="block text-xs mb-1">Unit wt (pcf, 0=auto)</label>
            <input type="number" className="w-full border rounded px-2 py-1" value={form.gamma ?? 0}
              step={5} onChange={(e) => setForm({ ...form, gamma: parseFloat(e.target.value) || null })} />
          </div>
          <div>
            <label className="block text-xs mb-1">phi&apos; (deg, 0=auto)</label>
            <input type="number" className="w-full border rounded px-2 py-1" value={form.phi ?? 0}
              step={1} onChange={(e) => setForm({ ...form, phi: parseFloat(e.target.value) || null })} />
          </div>
          <div>
            <label className="block text-xs mb-1">c_u (psf, 0=auto)</label>
            <input type="number" className="w-full border rounded px-2 py-1" value={form.c_u ?? 0}
              step={100} onChange={(e) => setForm({ ...form, c_u: parseFloat(e.target.value) || null })} />
          </div>
        </div>
        <button onClick={addLayer} className="mt-3 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Add Layer
        </button>
      </div>

      {/* Layer table */}
      {project.soil_layers.length > 0 ? (
        <div className="bg-white border rounded overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-3 py-2 text-left">#</th>
                <th className="px-3 py-2 text-left">Depth (ft)</th>
                <th className="px-3 py-2 text-left">Type</th>
                <th className="px-3 py-2 text-left">Description</th>
                <th className="px-3 py-2 text-left">N_spt</th>
                <th className="px-3 py-2 text-left">gamma</th>
                <th className="px-3 py-2 text-left">phi&apos;</th>
                <th className="px-3 py-2 text-left">c_u</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {project.soil_layers.map((l, i) => (
                <tr key={i} className="border-t">
                  <td className="px-3 py-2">{i + 1}</td>
                  <td className="px-3 py-2">{l.top_depth} - {l.top_depth + l.thickness}</td>
                  <td className="px-3 py-2">{l.soil_type}</td>
                  <td className="px-3 py-2">{l.description || "-"}</td>
                  <td className="px-3 py-2">{l.N_spt ?? "-"}</td>
                  <td className="px-3 py-2">{l.gamma || "auto"}</td>
                  <td className="px-3 py-2">{l.phi || "auto"}</td>
                  <td className="px-3 py-2">{l.c_u || "auto"}</td>
                  <td className="px-3 py-2">
                    <button onClick={() => removeLayer(i)} className="text-red-500 hover:text-red-700">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-gray-500">No layers defined. Add at least one soil layer to proceed.</p>
      )}
    </div>
  );
}
