import json
import os
import sys
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ["STRAVA_CLIENT_ID"]
CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
REDIRECT_URI = "http://localhost:8080/callback"
SCOPE = "activity:read_all"


class CallbackHandler(BaseHTTPRequestHandler):
    code: str | None = None
    error: str | None = None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)

        if "error" in params:
            CallbackHandler.error = params["error"][0]
            body = b"<h1>Authorization denied. You can close this tab.</h1>"
        else:
            CallbackHandler.code = params.get("code", [None])[0]
            body = b"<h1>Authorization successful! You can close this tab.</h1>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass  # suppress request logging


auth_url = "https://www.strava.com/oauth/authorize?" + urlencode({
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": SCOPE,
    "approval_prompt": "force",
})

print(f"Opening Strava authorization page...")
print(f"If the browser doesn't open, visit:\n  {auth_url}\n")
webbrowser.open(auth_url)

server = HTTPServer(("localhost", 8080), CallbackHandler)
server.timeout = 120
print("Waiting for callback on http://localhost:8080/callback (2 min timeout)...")

while CallbackHandler.code is None and CallbackHandler.error is None:
    server.handle_request()

server.server_close()

if CallbackHandler.error:
    print(f"Error: Strava returned '{CallbackHandler.error}'. Did you deny access?")
    sys.exit(1)

# Exchange authorization code for tokens
post_data = urlencode({
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": CallbackHandler.code,
    "grant_type": "authorization_code",
}).encode()

req = urllib.request.Request(
    "https://www.strava.com/oauth/token",
    data=post_data,
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    token_data = json.loads(resp.read())

athlete = token_data.get("athlete", {})
refresh_token = token_data["refresh_token"]

print(f"\nSuccess! Authorized as: {athlete.get('firstname', '')} {athlete.get('lastname', '')}")
print(f"Scopes granted: {token_data.get('scope', 'unknown')}")

# Write new refresh token back to .env
env_path = os.path.join(os.path.dirname(__file__), ".env")
with open(env_path, "r") as f:
    env_contents = f.read()

if "STRAVA_REFRESH_TOKEN=" in env_contents:
    import re
    env_contents = re.sub(r"STRAVA_REFRESH_TOKEN=.*", f"STRAVA_REFRESH_TOKEN={refresh_token}", env_contents)
else:
    env_contents += f"\nSTRAVA_REFRESH_TOKEN={refresh_token}\n"

with open(env_path, "w") as f:
    f.write(env_contents)

print(f"\n.env updated with new refresh token: {refresh_token}")
