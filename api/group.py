"""Vercel serverless function: Pile group analysis."""

import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.soil import SoilLayer, SoilProfile, SoilType
from core.group import group_analysis
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

            result = group_analysis(
                profile=profile,
                n_rows=body.get("n_rows", 2),
                n_cols=body.get("n_cols", 2),
                pile_width=section.depth,
                spacing=body.get("spacing", 36),
                embedment=body["embedment_depth"],
                Q_single_compression=body.get("Q_single_compression", 10000),
            )

            response = {
                "n_piles": result.n_piles,
                "n_rows": result.n_rows,
                "n_cols": result.n_cols,
                "spacing": result.spacing,
                "s_over_d": result.s_over_d,
                "eta_axial": result.eta_axial,
                "Q_group_individual": result.Q_group_individual,
                "Q_block": result.Q_block,
                "Q_group_governing": result.Q_group_governing,
                "p_multipliers": result.p_multipliers,
                "eta_lateral": result.eta_lateral,
                "method": result.method,
                "notes": result.notes,
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
