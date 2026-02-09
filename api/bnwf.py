"""Vercel serverless function: BNWF FEM analysis."""

import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.soil import SoilLayer, SoilProfile, SoilType
from core.sections import get_section
from core.bnwf import run_bnwf_analysis, BNWFLoadInput, BNWFOptions


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length))

        try:
            layers = []
            for ld in body["soil_layers"]:
                layers.append(SoilLayer(
                    top_depth=ld["top_depth"],
                    thickness=ld["thickness"],
                    soil_type=SoilType(ld["soil_type"]),
                    description=ld.get("description", ""),
                    N_spt=ld.get("N_spt"),
                    gamma=ld.get("gamma"),
                    phi=ld.get("phi"),
                    c_u=ld.get("c_u"),
                ))
            profile = SoilProfile(
                layers=layers,
                water_table_depth=body.get("water_table_depth"),
            )

            section = get_section(body["pile_section"])

            load_type = body.get("analysis_type", "static")
            if load_type not in ("static", "pushover_lateral", "pushover_axial"):
                load_type = "static"

            loads = BNWFLoadInput(
                V_axial=body.get("V_axial", 0),
                H_lateral=body.get("H_lateral", 0),
                M_ground=body.get("M_ground", 0),
                load_type=load_type,
                pushover_steps=body.get("pushover_steps", 15),
                pushover_max_mult=body.get("pushover_max_mult", 3.0),
            )

            options = BNWFOptions(
                n_elements=40,  # Reduced for serverless timeout
                bending_axis=body.get("bending_axis", "strong"),
                head_condition=body.get("head_condition", "free"),
                cyclic=body.get("cyclic", False),
                include_p_delta=body.get("include_p_delta", True),
                max_iter=150,
                tol=1e-4,
                solver="python",  # OpenSeesPy not available on Vercel
                pile_type=body.get("pile_type", "driven"),
            )

            result = run_bnwf_analysis(profile, section, body["embedment_depth"],
                                       loads, options)

            response = {
                "solver_used": result.solver_used,
                "analysis_type": result.analysis_type,
                "converged": result.converged,
                "iterations": result.iterations,
                "notes": result.notes,
                "y_ground_lateral": result.y_ground_lateral,
                "y_ground_axial": result.y_ground_axial,
                "M_max": result.M_max,
                "depth_M_max": result.depth_M_max,
                "P_critical": result.P_critical,
                "soil_reaction_q_lbs": result.soil_reaction_q_lbs,
                "K_head": result.K_head.tolist(),
                "depth_ft": result.depth_ft.tolist(),
                "deflection_lateral_in": result.deflection_lateral_in.tolist(),
                "deflection_axial_in": result.deflection_axial_in.tolist(),
                "moment_ft_lbs": result.moment_ft_lbs.tolist(),
                "shear_lbs": result.shear_lbs.tolist(),
                "axial_force_lbs": result.axial_force_lbs.tolist(),
                "soil_reaction_p_lb_in": result.soil_reaction_p_lb_in.tolist(),
                "soil_reaction_t_lb_in": result.soil_reaction_t_lb_in.tolist(),
                "pushover_load": result.pushover_load,
                "pushover_disp": result.pushover_disp,
                "pushover_axis": result.pushover_axis,
                "py_curves": [
                    {"depth_ft": py.depth_ft, "method": py.method,
                     "y": py.y.tolist(), "p": py.p.tolist()}
                    for py in result.py_curves
                ],
                "tz_curves": [
                    {"depth_ft": tz.depth_ft, "method": tz.method,
                     "z": tz.z.tolist(), "t": tz.t.tolist()}
                    for tz in result.tz_curves
                ],
                "qz_curve": {
                    "method": result.qz_curve.method,
                    "z": result.qz_curve.z.tolist(),
                    "q": result.qz_curve.q.tolist(),
                    "q_ult": result.qz_curve.q_ult,
                } if result.qz_curve else None,
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
