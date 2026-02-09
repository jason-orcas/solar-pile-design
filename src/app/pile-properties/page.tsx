"use client";

import { useProject } from "@/components/ProjectProvider";
import { PILE_SECTIONS } from "@/lib/api";

const SECTION_DATA: Record<string, { d: number; bf: number; A: number; w: number; Ix: number; Iy: number; Sx: number; Sy: number }> = {
  "W6x7":    { d: 5.80, bf: 3.94, A: 2.05, w: 7,    Ix: 12.2, Iy: 1.41,  Sx: 4.21,  Sy: 0.716 },
  "W6x9":    { d: 5.90, bf: 3.94, A: 2.64, w: 9,    Ix: 16.4, Iy: 1.83,  Sx: 5.56,  Sy: 0.929 },
  "W6x12":   { d: 6.03, bf: 4.00, A: 3.55, w: 12,   Ix: 22.1, Iy: 2.99,  Sx: 7.31,  Sy: 1.50  },
  "W6x15":   { d: 5.99, bf: 5.99, A: 4.43, w: 15,   Ix: 29.1, Iy: 9.32,  Sx: 9.72,  Sy: 3.11  },
  "W8x10":   { d: 7.89, bf: 3.94, A: 2.96, w: 10,   Ix: 30.8, Iy: 1.99,  Sx: 7.81,  Sy: 1.01  },
  "W8x13":   { d: 7.99, bf: 4.00, A: 3.84, w: 13,   Ix: 39.6, Iy: 2.73,  Sx: 9.91,  Sy: 1.37  },
  "W8x15":   { d: 8.11, bf: 4.01, A: 4.44, w: 15,   Ix: 48.0, Iy: 3.41,  Sx: 11.8,  Sy: 1.70  },
  "W8x18":   { d: 8.14, bf: 5.25, A: 5.26, w: 18,   Ix: 61.9, Iy: 7.97,  Sx: 15.2,  Sy: 3.04  },
  "C4x5.4":  { d: 4.00, bf: 1.58, A: 1.59, w: 5.4,  Ix: 3.85, Iy: 0.319, Sx: 1.93,  Sy: 0.283 },
  "C4x7.25": { d: 4.00, bf: 1.72, A: 2.13, w: 7.25, Ix: 4.59, Iy: 0.432, Sx: 2.29,  Sy: 0.343 },
};

export default function PileProperties() {
  const { project, update } = useProject();
  const sec = SECTION_DATA[project.pile_section] || SECTION_DATA["W6x9"];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Pile Properties</h2>

      <div className="grid grid-cols-2 gap-8 max-w-4xl">
        <div className="space-y-4">
          <h3 className="font-semibold">Section Selection</h3>
          <div>
            <label className="block text-sm mb-1">Steel Section</label>
            <select className="w-full border rounded px-3 py-2" value={project.pile_section}
              onChange={(e) => update({ pile_section: e.target.value })}>
              {PILE_SECTIONS.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>

          <div className="bg-gray-50 rounded p-3 text-sm space-y-1">
            <p className="font-medium mb-2">Section Properties</p>
            <p>Depth: {sec.d} in</p>
            <p>Flange Width: {sec.bf} in</p>
            <p>Area: {sec.A} in&sup2;</p>
            <p>Weight: {sec.w} plf</p>
            <p>I_x: {sec.Ix} in&sup4;</p>
            <p>I_y: {sec.Iy} in&sup4;</p>
            <p>S_x: {sec.Sx} in&sup3;</p>
            <p>S_y: {sec.Sy} in&sup3;</p>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="font-semibold">Installation &amp; Geometry</h3>
          <div>
            <label className="block text-sm mb-1">Embedment Depth (ft)</label>
            <input type="number" className="w-full border rounded px-3 py-2"
              value={project.embedment_depth} min={1} max={50} step={0.5}
              onChange={(e) => update({ embedment_depth: parseFloat(e.target.value) })} />
          </div>
          <div>
            <label className="block text-sm mb-1">Installation Method</label>
            <select className="w-full border rounded px-3 py-2" value={project.pile_type}
              onChange={(e) => update({ pile_type: e.target.value })}>
              <option value="driven">Driven</option>
              <option value="drilled">Drilled</option>
              <option value="helical">Helical</option>
            </select>
          </div>
          <div>
            <label className="block text-sm mb-1">Head Condition</label>
            <select className="w-full border rounded px-3 py-2" value={project.head_condition}
              onChange={(e) => update({ head_condition: e.target.value })}>
              <option value="free">Free</option>
              <option value="fixed">Fixed</option>
            </select>
          </div>
          <div>
            <label className="block text-sm mb-1">Bending Axis</label>
            <select className="w-full border rounded px-3 py-2" value={project.bending_axis}
              onChange={(e) => update({ bending_axis: e.target.value })}>
              <option value="strong">Strong Axis</option>
              <option value="weak">Weak Axis</option>
            </select>
          </div>

          <div className="bg-blue-50 rounded p-3 text-sm">
            <p className="font-medium">Pile weight in ground: {(sec.w * project.embedment_depth).toFixed(0)} lbs</p>
          </div>
        </div>
      </div>
    </div>
  );
}
