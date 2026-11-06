# Python 3 / Squeek Sprint / isolated Chromium tests against mocked public status responses.
"""Synthetic fixtures test the client only: never evidence of live hamster activity or badges."""
from __future__ import annotations
import argparse
import copy
import functools
import http.server
import json
from pathlib import Path
import threading
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / 'tests/fixtures/status.json').read_text(encoding='utf-8'))
CSP = next(h['value'] for entry in json.loads((ROOT/'site/vercel.json').read_text())['headers']
           for h in entry['headers'] if h['key'] == 'Content-Security-Policy')
API = 'https://api.squeekchain.com/v1/status'

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    def end_headers(self):
        self.send_header('Content-Security-Policy', CSP)
        super().end_headers()

def sample(**patch):
    data = copy.deepcopy(FIXTURE)
    stamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    data['measurement'].update(freshness='online', provenance='hardware', coreStatus='ACTIVE',
                               rpmMilli=60000, cumulativeWorkUnits='9007199254740993',
                               observedAt=stamp, receivedAt=stamp)
    data['measurement'].update(patch)
    return data

def run_suite(browser, origin, run):
    cases, errors, contexts = [], [], []
    def page_for(payload=None, offline=False, viewport=None):
        context = browser.new_context(viewport=viewport or {'width':1440,'height':1120},
                                      reduced_motion='reduce')
        contexts.append(context)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        state={'payload':payload if payload is not None else sample(), 'requests':[],
               'status':200,'offline':offline,'retry':'20'}
        def respond(route):
            state['requests'].append(dict(route.request.headers))
            if state['offline']:
                route.abort('failed')
            else:
                headers={'access-control-allow-origin':'*','content-type':'application/json',
                         'access-control-expose-headers':'ETag,Retry-After','etag':'"test-only-v1"',
                         'retry-after':state['retry']}
                route.fulfill(status=state['status'], headers=headers,
                              body='' if state['status']==304 else json.dumps(state['payload']))
        page.route(API, respond)
        page.clock.install()
        page.goto(origin, wait_until='networkidle')
        return page,state
    def passed(name):
        cases.append(name)
        print(f'PASS browser run {run}: {name}',flush=True)
    try:
        p,s=page_for(offline=True)
        expect(p.locator('#start')).to_be_disabled()
        p.locator('#practice').click()
        expect(p.locator('#overlay')).to_be_hidden()
        expect(p.locator('#mode-label')).to_have_text('PRACTICE / LOCAL SIMULATION')
        p.keyboard.press('p')
        expect(p.locator('#pause')).to_have_text('Resume')
        expect(p.locator('#wait')).to_be_visible()
        p.keyboard.press('p')
        expect(p.locator('#pause')).to_have_text('Pause')
        expect(p.locator('#wait')).to_be_hidden()
        p.locator('#left').click();p.locator('#right').click()
        p.locator('#sound').click();expect(p.locator('#sound')).to_have_attribute('aria-pressed','true')
        p.locator('#sound').click()
        p.locator('#restart').click();expect(p.locator('#time')).to_have_text('60s')
        p.screenshot(path=str(ROOT/f'evidence/sprint-v2-desktop-{run}.png'),full_page=True)
        passed('offline practice, keyboard pause, touch buttons, restart, sound toggle')

        p,s=page_for()
        expect(p.locator('#feed-pill')).to_have_text('LIVE HARDWARE')
        expect(p.locator('#start')).to_be_enabled()
        p.locator('#start').click()
        expect(p.locator('#mode-label')).to_have_text('LIVE EXPEDITION / HARDWARE')
        s['payload']=sample(cumulativeWorkUnits='9007199254741008')
        p.clock.fast_forward(5100)
        expect(p.locator('#work')).to_have_text('15')
        expect(p.locator('#habitat')).to_contain_text('AMBER CANYON')
        assert any('if-none-match' in r for r in s['requests'][1:]),'ETag was not reused'
        s['status']=304
        p.clock.fast_forward(5100)
        expect(p.locator('#work')).to_have_text('15')
        passed('fresh live start, exact BigInt delta, work-driven habitat and ETag/304 dedupe')

        s['status']=200;s['payload']=sample(coreStatus='IDLE',rpmMilli=0,cumulativeWorkUnits='9007199254741008')
        p.clock.fast_forward(5100)
        expect(p.locator('#wait')).to_contain_text('resting')
        expect(p.locator('#start')).to_be_disabled()
        oldtime=p.locator('#time').inner_text()
        p.clock.fast_forward(1500)
        expect(p.locator('#time')).to_have_text(oldtime)
        passed('resting wheel freezes run time and presents an honest wait state')

        s['payload']=sample(cumulativeWorkUnits='1')
        p.clock.fast_forward(5100)
        expect(p.locator('#overlay')).to_be_visible()
        expect(p.locator('#overlay-title')).to_have_text('A new wheel chapter.')
        expect(p.locator('#best')).to_have_text('—')
        passed('counter reset invalidates run without recording a live best')

        for label,patch in [('simulated',{'provenance':'simulated'}),('fault',{'coreStatus':'COUNTER_FAULT'}),
                            ('stale',{'freshness':'stale'}),('future',{'receivedAt':'2099-01-01T00:00:00Z'})]:
            q,_=page_for(sample(**patch));expect(q.locator('#start')).to_be_disabled()
            q.locator('#practice').click();expect(q.locator('#overlay')).to_be_hidden()
            passed(label+' readings cannot be used for live mode; practice remains playable')

        bad=sample();bad['schemaVersion']=2
        q,_=page_for(bad);expect(q.locator('#start')).to_be_disabled()
        expect(q.locator('#feed-pill')).to_have_text('UNAVAILABLE')
        passed('unsupported schema fails closed in real Chromium')

        q,t=page_for();t['status']=429
        q.clock.fast_forward(5100)
        expect(q.locator('#feed-pill')).to_have_text('UNAVAILABLE')
        count=len(t['requests']);q.clock.fast_forward(10000)
        assert len(t['requests'])==count,'Ignored Retry-After during rate limit'
        t['status']=200;t['payload']=sample()
        q.clock.fast_forward(11000)
        expect(q.locator('#feed-pill')).to_have_text('LIVE HARDWARE')
        passed('429 Retry-After is respected and polling recovers')

        q,t=page_for(sample(cumulativeWorkUnits='100'))
        q.locator('#start').click()
        q.keyboard.press('p');q.keyboard.press('p')
        t['payload']=sample(cumulativeWorkUnits='120')
        q.clock.fast_forward(5100)
        expect(q.locator('#work')).to_have_text('0')
        passed('resume without an intervening poll discards paused work')
        t['payload']=sample(cumulativeWorkUnits='1000',provenance='simulated')
        q.clock.fast_forward(5100)
        expect(q.locator('#wait')).to_be_visible()
        t['payload']=sample(cumulativeWorkUnits='125')
        q.clock.fast_forward(5100)
        expect(q.locator('#overlay')).to_be_hidden()
        expect(q.locator('#work')).to_have_text('0')
        passed('simulated samples cannot poison a running hardware counter')
        latest=sample(cumulativeWorkUnits='130')
        t['payload']=latest;q.clock.fast_forward(5100)
        expect(q.locator('#work')).to_have_text('5')
        t['offline']=True;q.clock.fast_forward(5100)
        expect(q.locator('#feed-pill')).to_have_text('UNAVAILABLE')
        t['offline']=False
        t['payload']=sample(cumulativeWorkUnits='110',observedAt='2026-01-01T00:00:00Z')
        q.clock.fast_forward(5100)
        expect(q.locator('#overlay')).to_be_hidden()
        expect(q.locator('#work')).to_have_text('5')
        expect(q.locator('#feed-pill')).to_have_text('UNAVAILABLE')
        t['payload']=sample(cumulativeWorkUnits='135')
        q.clock.fast_forward(11000)
        expect(q.locator('#feed-pill')).to_have_text('LIVE HARDWARE')
        expect(q.locator('#overlay')).to_be_hidden()
        passed('network recovery retains timestamp high-water and ignores old counters')

        q,t=page_for(viewport={'width':375,'height':812})
        q.locator('#practice').click();q.locator('#left').click();q.locator('#right').click()
        assert q.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile horizontal overflow'
        q.screenshot(path=str(ROOT/f'evidence/sprint-v2-mobile-{run}.png'),full_page=True)
        q.set_viewport_size({'width':320,'height':740})
        assert q.evaluate('document.documentElement.scrollWidth <= innerWidth'), '320px overflow'
        passed('mobile 375px and 320px fit, with usable touch controls')

        assert not errors,errors
        return {'run':run,'passed':len(cases),'cases':cases,'pageErrors':errors,
                'input':'synthetic schema-valid test fixtures; not live feed / badge evidence'}
    finally:
        for context in contexts:
            context.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repeat',type=int,default=1)
    args=parser.parse_args()
    (ROOT/'evidence').mkdir(exist_ok=True)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT/'site')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    results=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            try:
                for i in range(1,args.repeat+1):
                    results.append(run_suite(browser,f'http://127.0.0.1:{server.server_port}',i))
            finally:
                browser.close()
        target=ROOT/'evidence/sprint-v2-browser-tests.json'
        target.write_text(json.dumps({'suites':results,'suiteCount':len(results),
                                      'caseCount':sum(r['passed'] for r in results)},indent=2),encoding='utf-8')
        print(f'BROWSER VERIFIED suites={len(results)} cases={sum(r["passed"] for r in results)} evidence={target}',flush=True)
    finally:
        server.shutdown();server.server_close()

if __name__=='__main__':
    main()
