"""Minimal WhatsApp Cloud API webhook using only the standard library.

GET  /webhook  -> verification handshake (hub.challenge)
POST /webhook  -> runs each incoming text through main.handle()
Sending replies needs WHATSAPP_TOKEN and PHONE_NUMBER_ID; see README roadmap.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import main

VERIFY = os.getenv("WHATSAPP_VERIFY_TOKEN", "change-me")


class Hook(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        if q.get("hub.verify_token", [""])[0] == VERIFY:
            self.send_response(200); self.end_headers()
            self.wfile.write(q.get("hub.challenge", [""])[0].encode())
        else:
            self.send_response(403); self.end_headers()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                for m in change.get("value", {}).get("messages", []):
                    if m.get("type") == "text":
                        print(json.dumps(main.handle({"from": m["from"], "text": m["text"]["body"]})))
        self.send_response(200); self.end_headers()


if __name__ == "__main__":
    print("Listening on :8080/webhook")
    HTTPServer(("", 8080), Hook).serve_forever()
