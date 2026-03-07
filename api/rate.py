"""
POST /api/rate
Body: { event_id, event_name, event_date, event_type, action: "like" | "unlike" }
Upserts or deletes from Supabase ratings table.
Returns: { success: true }
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error
import urllib.parse


def _supabase(method, path, body=None):
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key  = os.environ.get("SUPABASE_ANON_KEY", "")
    if not base or not key:
        return 503, "Supabase not configured"

    headers = {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }
    data = json.dumps(body).encode() if body is not None else None
    req  = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))

            event_id   = body["event_id"]
            event_name = body["event_name"]
            event_date = body.get("event_date") or None
            event_type = body.get("event_type") or None
            action     = body.get("action", "like")
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self._respond(400, {"success": False, "error": str(exc)})
            return

        if action == "unlike":
            safe = urllib.parse.quote(event_id, safe="")
            status, _ = _supabase("DELETE", f"/rest/v1/ratings?event_id=eq.{safe}")
        else:
            status, _ = _supabase("POST", "/rest/v1/ratings", {
                "event_id":   event_id,
                "event_name": event_name,
                "event_date": event_date,
                "event_type": event_type,
            })

        ok = status in (200, 201, 204)
        self._respond(200 if ok else 500, {"success": ok})

    def _respond(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        pass
