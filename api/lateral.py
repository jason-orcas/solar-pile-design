"""Vercel serverless function: Lateral load analysis."""

import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.soil import SoilLayer, SoilProfile, SoilType
from core.lateral import solve_lateral
from core.sections import get_section


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
            axis = body.get("bending_axis", "strong")
            EI = section.EI_strong if axis == "strong" else section.EI_weak
            B = section.depth if axis == "strong" else section.width

            result = solve_lateral(
                profile=profile,
                pile_width=B,
                EI=EI,
                embedment=body["embedment_depth"],
                H=body.get("H", 1500),
                M_ground=body.get("M_ground", 0),
                head_condition=body.get("head_condition", "free"),
                cyclic=body.get("cyclic", False),
                n_elements=80,  # Reduced for serverless timeout
            )

            My = section.My_strong if axis == "strong" else section.My_weak
            My_ft_lbs = My * 1000 / 12

            response = {
                "H_applied": result.H_applied,
                "M_applied": result.M_applied,
                "head_condition": result.head_condition,
                "y_ground": result.y_ground,
                "M_max": result.M_max,
                "depth_M_max": result.depth_M_max,
                "depth_zero_defl": result.depth_zero_defl,
                "My_ft_lbs": My_ft_lbs,
                "dcr": abs(result.M_max) / My_ft_lbs if My_ft_lbs > 0 else 999,
                "converged": result.converged,
                "iterations": result.iterations,
                "notes": result.notes,
                "depth_ft": result.depth_ft.tolist(),
                "deflection_in": result.deflection_in.tolist(),
                "moment_ft_lbs": result.moment_ft_lbs.tolist(),
                "shear_lbs": result.shear_lbs.tolist(),
                "soil_reaction_lb_in": result.soil_reaction_lb_in.tolist(),
                "py_curves": [
                    {
                        "depth_ft": py.depth_ft,
                        "method": py.method,
                        "y": py.y.tolist(),
                        "p": py.p.tolist(),
                    }
                    for py in result.py_curves
                ],
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
