"""PERF-01: runnable Chromium worker checks, latency and CDP heap evidence."""
import sys,json,time
from pathlib import Path
root=Path(__file__).resolve().parents[3]; sys.path[:0]=[str(root/'tests/e2e/driving_code'),str(root/'tests/unit/driving_code')]
from test_server import start_test_server
from unit_tests_cell_cycle_worker import _TESTS
from playwright.sync_api import sync_playwright
port,server=start_test_server(root)
try:
 with sync_playwright() as p:
  b=p.chromium.launch(); page=b.new_page();page.goto(f'http://127.0.0.1:{port}/tests/unit/test_harness.html');page.wait_for_function('!!window.FitClientPool')
  cdp=page.context.new_cdp_session(page);cdp.send('Performance.enable');before=cdp.send('Performance.getMetrics');start=time.monotonic()
  rows=page.evaluate(_TESTS)
  worker_heaps=[]
  browser_cdp=b.new_browser_cdp_session()
  responses=[]
  browser_cdp.on('Target.receivedMessageFromTarget', lambda event: responses.append(event))
  for target in browser_cdp.send('Target.getTargets')['targetInfos']:
   if target['type']=='worker' and 'fit_worker' in target['url']:
    session=browser_cdp.send('Target.attachToTarget',{'targetId':target['targetId'],'flatten':False})['sessionId']
    browser_cdp.send('Target.sendMessageToTarget',{'sessionId':session,'message':json.dumps({'id':1,'method':'Runtime.getHeapUsage'})})
    page.wait_for_timeout(100)
    for response in responses:
     if response['sessionId']==session:
      reply=json.loads(response['message'])
      if reply.get('id')==1: worker_heaps.append(reply)
    browser_cdp.send('Target.detachFromTarget',{'sessionId':session})
  print(json.dumps({'workerHeaps':worker_heaps,'seconds':time.monotonic()-start,'results':rows,'before':before,'after':cdp.send('Performance.getMetrics')},indent=2)); assert all(r['pass'] for r in rows)
  b.close()
finally: server.shutdown()
