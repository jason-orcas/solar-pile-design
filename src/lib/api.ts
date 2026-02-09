/** API client for calling Python serverless functions. */

export interface SoilLayerInput {
  top_depth: number;
  thickness: number;
  soil_type: string;
  description?: string;
  N_spt?: number | null;
  gamma?: number | null;
  phi?: number | null;
  c_u?: number | null;
}

export interface ProjectState {
  project_name: string;
  soil_layers: SoilLayerInput[];
  water_table_depth: number | null;
  pile_section: string;
  embedment_depth: number;
  pile_type: string;
  head_condition: string;
  bending_axis: string;
  // Loads
  dead: number;
  live: number;
  snow: number;
  wind_down: number;
  wind_up: number;
  wind_lateral: number;
  wind_moment: number;
  lever_arm: number;
  seismic_lateral: number;
  seismic_vertical: number;
  seismic_moment: number;
  design_method: string;
  // Axial
  axial_method: string;
  FS_compression: number;
  FS_tension: number;
  cyclic: boolean;
  // Group
  group_n_rows: number;
  group_n_cols: number;
  group_spacing: number;
}

export const DEFAULT_PROJECT: ProjectState = {
  project_name: "New Project",
  soil_layers: [],
  water_table_depth: null,
  pile_section: "W6x9",
  embedment_depth: 10,
  pile_type: "driven",
  head_condition: "free",
  bending_axis: "strong",
  dead: 400,
  live: 0,
  snow: 0,
  wind_down: 0,
  wind_up: 1500,
  wind_lateral: 1500,
  wind_moment: 0,
  lever_arm: 4,
  seismic_lateral: 0,
  seismic_vertical: 0,
  seismic_moment: 0,
  design_method: "LRFD",
  axial_method: "auto",
  FS_compression: 2.5,
  FS_tension: 3.0,
  cyclic: false,
  group_n_rows: 1,
  group_n_cols: 1,
  group_spacing: 36,
};

export const PILE_SECTIONS = [
  "C4x5.4", "C4x7.25",
  "W6x7", "W6x9", "W6x12", "W6x15",
  "W8x10", "W8x13", "W8x15", "W8x18",
];

export const SOIL_TYPES = ["Sand", "Silt", "Clay", "Gravel", "Organic"];

async function post(url: string, body: unknown) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || "API error");
  }
  return res.json();
}

export async function runAxialAnalysis(project: ProjectState) {
  return post("/api/axial", {
    soil_layers: project.soil_layers,
    water_table_depth: project.water_table_depth,
    pile_section: project.pile_section,
    embedment_depth: project.embedment_depth,
    method: project.axial_method,
    pile_type: project.pile_type,
    FS_compression: project.FS_compression,
    FS_tension: project.FS_tension,
  });
}

export async function runLateralAnalysis(project: ProjectState) {
  return post("/api/lateral", {
    soil_layers: project.soil_layers,
    water_table_depth: project.water_table_depth,
    pile_section: project.pile_section,
    embedment_depth: project.embedment_depth,
    bending_axis: project.bending_axis,
    H: project.wind_lateral,
    M_ground: project.wind_lateral * project.lever_arm,
    head_condition: project.head_condition,
    cyclic: project.cyclic,
  });
}

export async function runGroupAnalysis(project: ProjectState, Q_single: number) {
  return post("/api/group", {
    soil_layers: project.soil_layers,
    water_table_depth: project.water_table_depth,
    pile_section: project.pile_section,
    embedment_depth: project.embedment_depth,
    n_rows: project.group_n_rows,
    n_cols: project.group_n_cols,
    spacing: project.group_spacing,
    Q_single_compression: Q_single,
  });
}

export async function runLoadCombinations(project: ProjectState) {
  return post("/api/loads", {
    dead: project.dead,
    live: project.live,
    snow: project.snow,
    wind_down: project.wind_down,
    wind_up: project.wind_up,
    wind_lateral: project.wind_lateral,
    wind_moment: project.wind_moment,
    seismic_vertical: project.seismic_vertical,
    seismic_lateral: project.seismic_lateral,
    seismic_moment: project.seismic_moment,
    lever_arm: project.lever_arm,
    method: project.design_method.toLowerCase() === "both" ? "both" : project.design_method.toLowerCase(),
  });
}
