# Python + Playwright · production planner browser check · public wallet reads only.
import json
import pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={'width': 1365, 'height': 900})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            response = page.goto('https://squeek.onerub.net/', wait_until='networkidle', timeout=45000)
            assert response is not None and response.status == 200
            page.locator('#load').click()
            page.wait_for_function("!document.querySelector('#load').disabled", timeout=90000)
            result = {
                'pageErrors': errors,
                'warning': page.locator('#warn').inner_text(),
                'planNote': page.locator('#planNote').inner_text(),
                'pairs': page.locator('#readyPairs').inner_text(),
                'log': page.locator('#log').inner_text(),
            }
            page.screenshot(path=str(ROOT / 'evidence/planner-production.png'), full_page=True)
            (ROOT / 'evidence/planner-production.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result))
            assert errors == [], result
            assert result['pairs'] == '0', result
            assert 'Read failed' not in result['warning'], result
        finally:
            browser.close()


if __name__ == '__main__':
    main()
