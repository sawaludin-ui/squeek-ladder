# Python · Genesis Navigator · real Chromium smoke test with public live APIs.
import functools
import http.server
import json
import pathlib
import threading
import sys
import importlib.util
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]

SPEC = importlib.util.spec_from_file_location('genesis_adapter', ROOT / 'site/api/genesis.py')
assert SPEC is not None and SPEC.loader is not None
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)

class QuietHandler(http.server.SimpleHTTPRequestHandler, ADAPTER.handler):
    def do_GET(self):
        if self.path.startswith('/api/genesis?'):
            ADAPTER.handler.do_GET(self)
        else:
            super().do_GET()

    def log_message(self, format, *args):
        pass


def main():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={'width': 1365, 'height': 900}, accept_downloads=True)
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('requestfailed', lambda r: print('REQUEST_FAILED', r.url, r.failure))
                page.on('console', lambda m: print('CONSOLE', m.type, m.text) if m.type == 'error' else None)
                target = sys.argv[1] if len(sys.argv) > 1 else f'http://127.0.0.1:{server.server_port}/genesis.html'
                response = page.goto(target, wait_until='domcontentloaded', timeout=30000)
                assert response is not None and response.status == 200
                page.wait_for_function("!document.querySelector('#refresh').disabled", timeout=30000)
                print('BROWSER_STATUS', page.locator('#status').inner_text())
                assert page.locator('#status').inner_text().startswith('Loaded public snapshots.'), errors
                assert page.locator('#metrics .metric').count() == 4
                assert page.locator('#actions article').count() == 9
                assert page.locator('#leaders tr').count() > 0
                assert page.locator('#catalogue details').count() > 0
                with page.expect_download() as info:
                    page.locator('#export').click()
                downloaded = info.value
                output = ROOT / 'evidence' / 'genesis-browser-export.json'
                downloaded.save_as(output)
                data = json.loads(output.read_text(encoding='utf-8'))
                assert data['profile']['code'] == 'pbsm54mn'
                assert data['profile']['valid'] is True
                assert errors == [], errors
                page.screenshot(path=str(ROOT / 'evidence' / 'genesis-desktop.png'), full_page=True)
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile overflow'
                page.screenshot(path=str(ROOT / 'evidence' / 'genesis-mobile.png'), full_page=True)
                print(json.dumps({'status': 'PASS', 'pageErrors': errors, 'profile': data['profile']['code'], 'aura': data['profile']['standing']['aura'], 'rank': data['profile']['standing']['rank'], 'badges': len(data['badges']['badges']), 'export': str(output), 'mobileOverflow': False}))
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()

if __name__ == '__main__':
    main()
