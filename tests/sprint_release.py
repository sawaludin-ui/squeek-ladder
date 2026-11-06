# Python 3 / Squeek Sprint / read-only production, source, schema and Chromium verification.
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import subprocess
import requests
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
ORIGIN='https://squeek.onerub.net'
RAW='https://raw.githubusercontent.com/sawaludin-ui/squeek-ladder/main/'
FILES=['index.html','sprint.css','sprint.js','sprint-engine.js','status-validator.js','favicon.svg']

def main():
    http=requests.Session()
    report={'verifiedAt':datetime.now(timezone(timedelta(hours=7))).isoformat(),'files':[],'sensitivePaths':[]}
    for filename in FILES:
        local=(ROOT/'site'/filename).read_bytes()
        r=http.get(ORIGIN+'/'+('' if filename=='index.html' else filename),timeout=30)
        r.raise_for_status();assert r.content==local, 'Production drift: '+filename
        s=http.get(RAW+filename,timeout=30);s.raise_for_status()
        assert s.content==local,'Public source drift: '+filename
        report['files'].append({'name':filename,'productionHttp':r.status_code,'sourceHttp':s.status_code,
                                'sha256':hashlib.sha256(local).hexdigest()})
        if filename=='index.html':
            required=['content-security-policy','x-content-type-options','referrer-policy','permissions-policy']
            report['headers']={k:r.headers.get(k) for k in required}
            assert all(report['headers'].values()),'Missing security header'
    source=http.get(RAW+'README.md',timeout=30);source.raise_for_status()
    assert source.content==(ROOT/'README.md').read_bytes(),'Public README drift'
    for path in ['/.env','/.env.local','/.vercel/project.json','/a.json']:
        r=http.get(ORIGIN+path,timeout=30);assert r.status_code==404,(path,r.status_code)
        report['sensitivePaths'].append({'path':path,'http':r.status_code})
    schema=http.get('https://docs.squeekchain.com/assets/api/status.json',timeout=30);schema.raise_for_status()
    assert schema.json()==json.loads((ROOT/'docs/status.schema.json').read_text()),'Pinned official schema changed'
    feed=http.get('https://api.squeekchain.com/v1/status',timeout=30);feed.raise_for_status()
    (ROOT/'evidence/sprint-v2-real-feed.json').write_text(json.dumps(feed.json(),indent=2),encoding='utf-8')
    check=subprocess.run(['node','-e',"const E=require('./sprint-engine.js'),fs=require('fs');const m=E.parseStatus(JSON.parse(fs.readFileSync('evidence/sprint-v2-real-feed.json','utf8')));console.log(JSON.stringify({schemaValidated:true,liveEligible:E.isLive(m),coreStatus:m.coreStatus,rpmMilli:m.rpmMilli,provenance:m.provenance,observedAt:m.observedAt,receivedAt:m.receivedAt}));"],cwd=ROOT,capture_output=True,text=True)
    assert check.returncode==0,check.stderr
    report['realFeed']=json.loads(check.stdout)
    errors=[];responses=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={'width':1440,'height':1120})
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('response',lambda r:responses.append({'url':r.url,'http':r.status}) if 'api.squeekchain.com/v1/status' in r.url else None)
            page.goto(ORIGIN,wait_until='networkidle',timeout=60000)
            expect(page.locator('#feed-pill')).not_to_have_text('CONNECTING',timeout=20000)
            report['productionFeedLabel']=page.locator('#feed-pill').inner_text()
            report['productionFeedDetail']=page.locator('#feed-detail').inner_text()
            assert report['productionFeedLabel'] in ['LIVE HARDWARE','RESTING'], 'Real production feed was not admitted'
            assert responses and any(r['http'] in (200,304) for r in responses),'No successful real browser feed request'
            page.locator('#practice').click();expect(page.locator('#overlay')).to_be_hidden()
            page.keyboard.press('ArrowLeft');page.keyboard.press('ArrowRight');page.keyboard.press('p')
            expect(page.locator('#pause')).to_have_text('Resume')
            page.screenshot(path=str(ROOT/'evidence/sprint-v2-production-desktop.png'),full_page=True)
            page.set_viewport_size({'width':375,'height':812})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Mobile overflow'
            page.screenshot(path=str(ROOT/'evidence/sprint-v2-production-mobile.png'),full_page=True)
            assert not errors,errors
            report['browser']={'pageErrors':errors,'realFeedResponses':responses,'practicePlayable':True,'mobileFits':True}
        finally:
            browser.close()
    target=ROOT/'evidence/sprint-v2-release.json'
    target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    print('RELEASE_VERIFIED',target)

if __name__=='__main__':
    main()
