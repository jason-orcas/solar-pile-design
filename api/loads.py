"""Vercel serverless function: Load combinations."""

import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.loads import LoadInput, generate_lrfd_combinations, generate_asd_combinations


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length))

        try:
            load_input = LoadInput(
                dead=body.get("dead", 0),
                live=body.get("live", 0),
                snow=body.get("snow", 0),
                wind_down=body.get("wind_down", 0),
                wind_up=body.get("wind_up", 0),
                wind_lateral=body.get("wind_lateral", 0),
                wind_moment=body.get("wind_moment", 0),
                seismic_vertical=body.get("seismic_vertical", 0),
                seismic_lateral=body.get("seismic_lateral", 0),
                seismic_moment=body.get("seismic_moment", 0),
                lever_arm=body.get("lever_arm", 4.0),
            )

            method = body.get("method", "both")

            response = {}
            if method in ("lrfd", "both"):
                lrfd = generate_lrfd_combinations(load_input)
                response["lrfd"] = [
                    {"name": lc.name, "V_comp": lc.V_comp, "V_tens": lc.V_tens,
                     "H_lat": lc.H_lat, "M_ground": lc.M_ground}
                    for lc in lrfd
                ]
            if method in ("asd", "both"):
                asd = generate_asd_combinations(load_input)
                response["asd"] = [
                    {"name": lc.name, "V_comp": lc.V_comp, "V_tens": lc.V_tens,
                     "H_lat": lc.H_lat, "M_ground": lc.M_ground}
                    for lc in asd
                ]

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
