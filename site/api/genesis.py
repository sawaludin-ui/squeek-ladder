# Python stdlib · Vercel public-data adapter · GET-only, fixed upstream, no sessions or secrets.
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

UPSTREAM = 'https://community.squeekchain.com/v1/community'


def upstream_url(request_path):
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(request_path).query)
    resource = query.get('resource', [''])[0]
    if resource in ('aura/badges', 'leaderboard'):
        return UPSTREAM + '/' + resource
    if resource == 'profile':
        code = query.get('code', [''])[0]
        if re.fullmatch(r'[A-Za-z0-9_-]{1,64}', code):
            return UPSTREAM + '/profiles/' + urllib.parse.quote(code, safe='')
    raise ValueError('Unsupported public resource or invite code')


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            url = upstream_url(self.path)
        except ValueError as error:
            self.respond(400, {'error': str(error)})
            return
        try:
            request = urllib.request.Request(url, headers={
                'Accept': 'application/json',
                'User-Agent': 'Squeek-Ladder/1.0 public-read-only',
            })
            with urllib.request.urlopen(request, timeout=12) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError('Upstream response too large')
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError('Unexpected upstream response')
            self.respond(200, data)
        except urllib.error.HTTPError as error:
            self.respond(502, {'error': 'Public upstream returned HTTP ' + str(error.code)})
        except (OSError, ValueError) as error:
            self.respond(502, {'error': 'Public upstream unavailable: ' + type(error).__name__})

    def respond(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'public, max-age=0, s-maxage=30' if status == 200 else 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)
