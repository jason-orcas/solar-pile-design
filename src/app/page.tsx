"use client";

import { useProject } from "@/components/ProjectProvider";

export default function ProjectSetup() {
  const { project, update, reset } = useProject();

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Project Setup</h2>

      <div className="grid grid-cols-2 gap-6 max-w-3xl">
        <div>
          <label className="block text-sm font-medium mb-1">Project Name</label>
          <input
            type="text"
            className="w-full border rounded px-3 py-2"
            value={project.project_name}
            onChange={(e) => update({ project_name: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Design Method</label>
          <select
            className="w-full border rounded px-3 py-2"
            value={project.design_method}
            onChange={(e) => update({ design_method: e.target.value })}
          >
            <option>LRFD</option>
            <option>ASD</option>
            <option>Both</option>
          </select>
        </div>
      </div>

      <div className="mt-8 flex gap-4">
        <button
          onClick={() => {
            const data = JSON.stringify(project, null, 2);
            const blob = new Blob([data], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${project.project_name.replace(/\s+/g, "_")}.json`;
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Export Project (JSON)
        </button>

        <label className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 cursor-pointer">
          Import Project
          <input
            type="file"
            accept=".json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              const reader = new FileReader();
              reader.onload = (ev) => {
                try {
                  const data = JSON.parse(ev.target?.result as string);
                  update(data);
                } catch {
                  alert("Invalid project file");
                }
              };
              reader.readAsText(file);
            }}
          />
        </label>

        <button
          onClick={reset}
          className="px-4 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200"
        >
          Reset All
        </button>
      </div>

      <div className="mt-8 p-4 bg-blue-50 rounded text-sm text-blue-800">
        Use the sidebar to navigate through each step: define your soil profile, select pile properties,
        enter loads, then run axial, lateral, and group analyses.
      </div>
    </div>
  );
}
