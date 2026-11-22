"""CI-only Chromium coverage at a GitHub Pages project subpath."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import shutil,tempfile,threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def main():
 screenshots=ROOT/'browser-checks';screenshots.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory() as temporary:
  shutil.copytree(ROOT/'dist',Path(temporary)/'mushroomcalendar')
  server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=temporary));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1080});errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(f'http://127.0.0.1:{server.server_port}/mushroomcalendar/');page.wait_for_function("document.querySelector('#stat-count').textContent !== '—'")
    assert page.locator('#records tr').count()>0
    assert page.locator('#map circle').count()>0
    assert 'complete selected queries' in page.locator('#snapshot-status').inner_text()
    page.locator('#area').select_option('halifax');assert page.locator('#region-title').inner_text()=='Halifax, NS'
    page.locator('#resolution').select_option('week');assert 'Obscured month-only records are excluded' in page.locator('#chart-summary').inner_text()
    page.locator('#resolution').select_option('month');page.locator('#month-buttons button').nth(9).click();assert 'Oct' in page.locator('#active-filters').inner_text()
    page.locator('#search').fill('<img src=x onerror=alert(1)>');assert page.locator('#stat-count').inner_text()=='0';assert page.locator('img').count()==0
    page.locator('#reset').click()
    with page.expect_download() as result:page.locator('#download').click()
    assert result.value.suggested_filename.endswith('.csv')
    options=page.locator('#snapshot option').evaluate_all('(items)=>items.map(x=>x.value)');page.locator('#snapshot').select_option(options[-1]);page.wait_for_function("!document.querySelector('#snapshot').disabled")
    assert page.locator('#error').is_hidden()
    page.screenshot(path=str(screenshots/'desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(screenshots/'mobile.png'),full_page=True)
    geometry=page.evaluate("""() => ({viewport:innerWidth,document:document.documentElement.scrollWidth,
      wide:[...document.querySelectorAll('body *')].map(el=>({tag:el.tagName,id:el.id,
        className:typeof el.className==='string'?el.className:'',right:el.getBoundingClientRect().right}))
        .filter(el=>el.right>innerWidth+1).slice(0,20)})""")
    assert geometry['document']<=geometry['viewport'],geometry
    assert not errors,errors;browser.close()
   print('Browser checks passed: source data, filters, seasons, privacy map, CSV, archives and mobile subpath')
  finally:server.shutdown()
if __name__=='__main__':main()
