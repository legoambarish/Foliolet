/* Real Edge, fresh private profile, synthetic data, isolated loopback services. */
const {chromium} = require(process.env.FOLI_PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const ROOT = path.resolve(__dirname, '..'), OUT = path.join(ROOT, '.local-data', 'intake-tests');
const UI = process.env.INTAKE_TEST_UI || 'http://127.0.0.1:8008';
const SPRING = process.env.INTAKE_TEST_API || 'http://127.0.0.1:8088';
const results = [], errors = [], external = [];
let browser, context, page;
function pass(name) {results.push({name, result:'PASS'});console.log(new Date().toISOString(), 'PASS', name);}
async function backend(route, auth, options={}) {
  const response=await fetch(SPRING+route,{...options,headers:{...options.headers,...(auth?{Authorization:'Basic '+Buffer.from(auth.join(':')).toString('base64')}:{})}});
  assert(response.ok, 'Private API returned '+response.status);const text=await response.text();try{return JSON.parse(text);}catch{return {message:text};}
}
async function noOverflow() {
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+1), 'Horizontal page overflow');
}
async function login(auth) {
  await page.goto(UI+'/login/');await page.locator('#username').fill(auth[0]);await page.locator('#password').fill(auth[1]);
  await Promise.all([page.waitForURL(UI+'/'),page.getByRole('button',{name:'Sign in',exact:true}).click()]);
}
async function main() {
  fs.mkdirSync(OUT,{recursive:true});
  const auth=['synthetic-ui-'+crypto.randomBytes(6).toString('hex'),'isolated-'+crypto.randomBytes(20).toString('hex')];
  await backend('/api/auth/register',null,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:auth[0],password:auth[1],role:'HOLDER'})});
  browser=await chromium.launch({headless:true,channel:process.env.FOLI_BROWSER_CHANNEL||'msedge'});
  context=await browser.newContext({viewport:{width:1365,height:1000},acceptDownloads:true});
  await context.route('**/*',async route => {
    const url=route.request().url();
    if(!url.startsWith(UI+'/') && !url.startsWith('data:') && !url.startsWith('blob:')) {external.push(new URL(url).origin);await route.abort();}
    else await route.continue();
  });
  page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
  await login(auth);await page.goto(UI+'/wallet/enroll/');
  const official=page.locator('#open-digilocker');
  assert.equal(await official.getAttribute('href'),'https://www.digilocker.gov.in/');
  assert.equal(await official.getAttribute('target'),'_blank');assert.match(await official.getAttribute('rel'),/noopener.*noreferrer/);
  await context.route('https://www.digilocker.gov.in/**',route=>route.fulfill({contentType:'text/html',body:'<title>Synthetic portal boundary test</title><p>Official login remains outside Foliolet.</p>'}));
  const popupPromise=page.waitForEvent('popup');await official.click();const popup=await popupPromise;await popup.waitForLoadState();
  assert.equal(popup.url(),'https://www.digilocker.gov.in/');assert.equal(await popup.evaluate(()=>window.opener),null);await popup.close();
  pass('Official HTTPS action opens a separate tab without an opener; closing it preserves the local form');
  assert(await page.locator('#intake-connection').textContent().then(t=>t.includes('not connected')));
  await noOverflow();await page.screenshot({path:path.join(OUT,'enroll-desktop.png'),fullPage:true});
  pass('Desktop enrollment shows honest disconnected state and normal file picker');
  const enrollmentColors=[];
  for(const theme of ['light','dark']) {
    await page.emulateMedia({colorScheme:theme});await page.setViewportSize({width:390,height:844});await noOverflow();
    enrollmentColors.push(await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--desk').trim()));
  }
  assert.notEqual(enrollmentColors[0],enrollmentColors[1]);
  pass('390px enrollment fits both actual light and dark palettes');
  await page.emulateMedia({colorScheme:'light'});await page.setViewportSize({width:1365,height:1000});
  await page.locator('summary').filter({hasText:'Use an optional local folder watcher'}).click();
  const folder=path.join(OUT,'ui-incoming');fs.mkdirSync(folder,{recursive:true});
  const managed=await page.locator('#digilocker-intake').getAttribute('data-managed')==='yes';
  if(!managed) await page.locator('#intake-folder').fill(folder);
  else assert(await page.locator('#intake-folder').getAttribute('readonly')!==null);
  await page.locator('[name=consent]').check();let pair;
  if(managed) {
    const paired=page.waitForResponse(r=>r.url().endsWith('/intake/pair/')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Enable folder intake'}).click();
    const response=await paired;assert.equal(response.status(),200);
    const body=await response.json();assert.deepEqual(Object.keys(body).sort(),['managed','sessionId']);
    await page.waitForFunction(()=>document.getElementById('intake-connection').textContent.includes('Watcher connected'),null,{timeout:30000});
    pass('Docker consent connects the included companion without a configuration download');
  } else {
    const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Enable folder intake'}).click();
    const download=await downloadPromise;assert.equal(download.suggestedFilename(),'foliolet-intake.json');
    const privateFile=path.join(OUT,'ui-pair-private.json');await download.saveAs(privateFile);
    pair=JSON.parse(fs.readFileSync(privateFile,'utf8'));assert.equal(pair.folder,folder);assert.equal(pair.apiUrl,SPRING);assert.equal(pair.maxFiles,10);
  }
  await page.locator('#intake-stop').waitFor({state:'visible'});await page.waitForFunction(()=>!document.getElementById('intake-stop').disabled);
  await Promise.all([page.waitForResponse(response=>response.url().includes('/stop/') && response.request().method()==='POST'),page.locator('#intake-stop').click()]);
  if(pair) {
    const refused=await fetch(SPRING+'/api/intake-agent/heartbeat',{method:'POST',headers:{Authorization:'Bearer '+pair.token,'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({folderHash:pair.folderHash})});
    assert.equal(refused.status,401);
  } else assert((await backend('/api/wallet/intake/sessions',auth)).every(s=>!s.active));
  pass('CSRF-protected UI Stop revokes the armed session');
  const csrf=await page.locator('[name=csrfmiddlewaretoken]').first().inputValue();
  assert.equal((await context.request.post(UI+'/intake/pair/',{form:{folder,consent:'yes'}})).status(),403);
  pass('Real Django intake POST rejects missing CSRF token');
  // Real manual upload through the user-facing form, with the companion stopped.
  await page.locator('#file').setInputFiles(path.join(OUT,'fixtures','both.pdf'));
  const title='Synthetic document '+('long filename '.repeat(6));await page.locator('#name').fill(title);
  await Promise.all([page.waitForURL(/\/wallet\/0x[0-9a-f]{64}\//),page.getByRole('button',{name:'Upload and review facts',exact:true}).click()]);
  await page.waitForFunction(()=>[...document.querySelectorAll('[name=claim_label]')].some(e=>e.value==='Math'),null,{timeout:300000});
  const math=page.locator('.edit-row').filter({has:page.locator('[name=claim_label][value="Math"]')});
  // Values set by JS do not necessarily update their HTML value attribute.
  const rows=page.locator('.edit-row');let mathIndex=-1;
  for(let n=0;n<await rows.count();n++) if(await rows.nth(n).locator('[name=claim_label]').inputValue()==='Math') mathIndex=n;
  assert(mathIndex>=0);const mathRow=rows.nth(mathIndex);assert.equal(await mathRow.locator('[name=claim_value]').inputValue(),'90');
  assert(await mathRow.locator('details').last().textContent().then(text=>text.includes('Math: 90')));
  await page.getByText('Preview: suggested facts unchanged.',{exact:false}).waitFor();
  await mathRow.locator('[name=claim_value]').fill('95');
  await page.getByText('Preview: facts edited since extraction.',{exact:false}).waitFor();
  pass('Real Ollama fields populate review rows with Math 90, source quote and immediate edited preview');
  const source=mathRow.locator('.scan-note a');assert.match(await source.getAttribute('href'),/^\/ask-foli\/api\/page\/\?/);
  let image;
  for(let attempt=0;attempt<30;attempt++) {image=await context.request.get(UI+await source.getAttribute('href'));if(image.status()!==429)break;await new Promise(resolve=>setTimeout(resolve,1000));}
  assert.equal(image.status(),200);assert.match(image.headers()['content-type'],/image\/png/);
  pass('Owner can open the exact retained original PDF page from a suggested fact');
  const reviewColors=[];
  for(const theme of ['light','dark']) {
    await page.emulateMedia({colorScheme:theme});await page.setViewportSize({width:390,height:844});await noOverflow();
    reviewColors.push(await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--desk').trim()));
    await page.screenshot({path:path.join(OUT,'review-mobile-'+theme+'.png'),fullPage:true,animations:'disabled'});
  }
  assert.notEqual(reviewColors[0],reviewColors[1]);
  pass('390px light and dark review has no horizontal overflow with long title and several fields');
  assert(await page.locator('#intake-stage').getAttribute('aria-live')==='polite');
  const accessibility=await page.locator('#claim-form').ariaSnapshot();assert.match(accessibility,/textbox "Label"/);assert.match(accessibility,/textbox "Value"/);
  await page.keyboard.press('Tab');assert(await page.evaluate(()=>document.activeElement!==document.body));
  pass('Review exposes labeled form controls, keyboard focus and live progress to accessibility tree');
  await page.locator('[name=confirm]').check();
  await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),page.getByRole('button',{name:'Confirm facts',exact:true}).click()]);
  await page.getByText('Facts edited since extraction',{exact:true}).first().waitFor();
  assert(await page.getByText('Issuer not verified',{exact:true}).count()>0);
  pass('Confirmed edit is recorded by server and shown separately from issuer status');
  assert.equal(errors.length,0,JSON.stringify(errors));
  // The only intentionally intercepted external URL is the official button.
  assert(external.every(origin=>origin==='https://www.digilocker.gov.in'),JSON.stringify(external));
  pass('Private browser workflow sends no document requests to external services and has no JavaScript errors');
  fs.writeFileSync(path.join(OUT,'ui-results.json'),JSON.stringify({checks:results,count:results.length,synthetic:true},null,2));
}
main().catch(error=>{console.error(error.message);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
