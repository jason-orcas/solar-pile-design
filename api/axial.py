"""Vercel serverless function: Axial capacity analysis."""

import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler

# Add project root so we can import shared core/
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.soil import SoilLayer, SoilProfile, SoilType
from core.axial import axial_capacity
from core.sections import get_section


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length))

        try:
            # Build soil profile
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

            # Get pile section
            section = get_section(body["pile_section"])

            # Run analysis
            result = axial_capacity(
                profile=profile,
                pile_perimeter=section.perimeter,
                pile_tip_area=section.tip_area,
                embedment_depth=body["embedment_depth"],
                method=body.get("method", "auto"),
                pile_type=body.get("pile_type", "driven"),
                FS_compression=body.get("FS_compression", 2.5),
                FS_tension=body.get("FS_tension", 3.0),
            )

            response = {
                "method": result.method,
                "Q_s": result.Q_s,
                "Q_b": result.Q_b,
                "Q_ult_compression": result.Q_ult_compression,
                "Q_ult_tension": result.Q_ult_tension,
                "Q_allow_compression": result.Q_allow_compression,
                "Q_allow_tension": result.Q_allow_tension,
                "FS_compression": result.FS_compression,
                "FS_tension": result.FS_tension,
                "phi_compression": result.phi_compression,
                "phi_tension": result.phi_tension,
                "Q_r_compression": result.Q_r_compression,
                "Q_r_tension": result.Q_r_tension,
                "layer_contributions": result.layer_contributions,
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
