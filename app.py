"""Offline Guardian X demo. Run: python app.py --port 8765"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import argparse
import json
from pathlib import Path

from guardian import Policy, hold_value, losses, mixed_residual, select_action, thresholds

ROOT = Path(__file__).resolve().parent


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlparse(self.path).path not in {"/", "/index.html"}:
            self.send_error(404)
            return
        data = (ROOT / "index.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if urlparse(self.path).path != "/api/evaluate":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 8192 or size <= 0:
                raise ValueError("Invalid request size")
            request = json.loads(self.rfile.read(size))
            p = float(request["risk"])/100
            sensitivity = float(request["sensitivity"])/100
            false_positive = float(request["false_positive"])/100
            rate = mixed_residual([(.5,.02), (.3,.03), (.2,float(request["social_rate"])/100)])
            policy = Policy(residual_attack_rate=rate)
            action = select_action(p, policy)
            current_losses = losses(p, policy)
            hold = hold_value(p, sensitivity, false_positive, policy, request.get("evidence", "E2"))
            result = {"decision": action, "losses": current_losses, "thresholds": thresholds(policy),
                      "residual": rate, "hold": hold,
                      "disclaimer": "Educational simulation; illustrative inputs and costs; no real account access."}
            data = json.dumps(result, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.send_response(400)
            data = json.dumps({"error": str(exc)}).encode()
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Guardian X PRISM demo")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print(f"Guardian X is running: http://127.0.0.1:{args.port}")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
