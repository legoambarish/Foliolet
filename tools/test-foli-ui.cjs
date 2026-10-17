/* Real Edge/Chromium UI gate. Only newly enrolled synthetic documents are used. */
const {chromium} = require(process.env.FOLI_PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, '.local-data', 'foli');
const UI = 'http://127.0.0.1:8000';
const SPRING = 'http://127.0.0.1:8080';
const events = [], errors = [], external = [];
let browser, context, page;
function pass(name, detail) { events.push({name, detail, result: 'PASS'}); console.log(new Date().toISOString(), 'PASS', name); }
async function backend(route, auth, options = {}) {
  const response = await fetch(SPRING + route, {...options, headers: {...options.headers,
    ...(auth ? {'Authorization': 'Basic ' + Buffer.from(auth.join(':')).toString('base64')} : {})}});
  assert(response.ok, route + ' returned ' + response.status);
  const text = await response.text(); try { return JSON.parse(text); } catch (_) { return {message: text}; }
}
async function fixture() {
  const auth = ['foli-ui-' + crypto.randomBytes(5).toString('hex'), crypto.randomBytes(20).toString('base64url')];
  await backend('/api/auth/register', null, {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username: auth[0], password: auth[1], role: 'HOLDER'})});
  const documents = {};
  for (const [filename, title] of [['long-contract-125-pages.pdf', 'Service agreement · 125 pages'],
    ['scan.pdf', 'Scanned notice'], ['unsupported.docx', 'Unsupported draft'], ['injection.txt', 'Notes <img src=x onerror=window.__foliXss=1>']]) {
    const file = path.join(OUT, 'fixtures', filename);
    const form = new FormData(); form.set('file', new Blob([fs.readFileSync(file)]), filename);
    form.set('displayName', title); form.set('category', 'Other');
    const document = await backend('/api/wallet/documents', auth, {method: 'POST', body: form});
    documents[filename] = {id: document.id, title};
  }
  fs.writeFileSync(path.join(OUT, 'ui-fixture.json'), JSON.stringify({auth, documents}, null, 2));
  return {auth, documents};
}
async function waitIdle(timeout = 200000) { await page.locator('#foli-progress').waitFor({state: 'hidden', timeout}); }
async function select(title) { await page.locator('#foli-documents .foli-doc').filter({hasText: title}).click(); await waitIdle(); }
async function ask(question) {
  await page.locator('#foli-question').fill(question); await page.locator('#foli-question').press('Enter'); await waitIdle();
}
async function main() {
  const data = await fixture(); pass('Isolated synthetic user and four documents enrolled');
  browser = await chromium.launch({headless: true, channel: process.env.FOLI_BROWSER_CHANNEL || 'msedge'});
  context = await browser.newContext({viewport: {width: 1440, height: 1050}, colorScheme: 'light'});
  await context.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.protocol === 'http:' && ['127.0.0.1', 'localhost'].includes(url.hostname)) return route.continue();
    external.push(url.origin); return route.abort('blockedbyclient');
  });
  page = await context.newPage(); page.on('pageerror', error => errors.push(error.message));
  await page.goto(UI + '/login/'); await page.locator('[name=username]').fill(data.auth[0]);
  await page.locator('[name=password]').fill(data.auth[1]);
  await Promise.all([page.waitForURL(UI + '/'), page.locator('form button').filter({hasText: /sign in/i}).click()]);
  await page.goto(UI + '/ask-foli/');
  await page.locator('#foli-health-label').filter({hasText: 'Local model ready'}).waitFor();
  await page.locator('#foli-documents .foli-doc').first().waitFor();
  assert.equal(await page.locator('.primary-nav a[aria-current=page]').textContent(), 'Ask Foli');
  await page.screenshot({path: path.join(OUT, 'ui-desktop.png'), fullPage: true}); pass('Native desktop interface and live local health');
  await page.locator('#foli-question').fill('First line'); await page.locator('#foli-question').press('Shift+Enter');
  await page.locator('#foli-question').type('Second line');
  assert.match(await page.locator('#foli-question').inputValue(), /First line\nSecond line/); pass('Shift+Enter inserts a newline');
  await ask('Write a short haiku about careful reading.');
  assert.match(await page.locator('#foli-log').textContent(), /General explanation/); pass('Unusual read-oriented conversation reaches real Ollama');
  await select(data.documents['long-contract-125-pages.pdf'].title);
  assert.match(await page.locator('#foli-coverage-summary').textContent(), /125\/125 readable/);
  assert(!await page.locator('#foli-log').textContent()); pass('Document switch clears previous context and reads all 125 pages');
  await ask('What is the dormant-account administration charge, and when is it payable?');
  await page.locator('.foli-message-assistant').last().locator('.foli-citation').first().waitFor();
  assert.match(await page.locator('#foli-log').textContent(), /9300/);
  await page.screenshot({path: path.join(OUT, 'ui-answer.png'), fullPage: true}); pass('Real document answer contains fee and matched source citation');
  await page.locator('.foli-message-assistant').last().locator('.foli-citation').first().click();
  await page.locator('#foli-source-text mark').waitFor(); assert.match(await page.locator('#foli-source-text mark').textContent(), /9300/);
  await page.locator('#foli-original-toggle').click();
  await page.waitForFunction(() => document.getElementById('foli-page-image').naturalWidth > 0);
  await page.screenshot({path: path.join(OUT, 'ui-source.png'), fullPage: true});
  await page.keyboard.press('Escape'); pass('Exact highlighted source and authenticated rendered original');
  await page.locator('#foli-review').click(); await waitIdle();
  assert.equal(await page.locator('.foli-finding').count(), 40);
  assert.match(await page.locator('#foli-log').textContent(), /Page\/segment 125/);
  await page.getByLabel('Filter fine-print findings').selectOption('exceptions');
  assert(await page.locator('.foli-finding:visible').count() >= 3);
  await page.screenshot({path: path.join(OUT, 'ui-review.png'), fullPage: true}); pass('Whole-document review, final-page finding and category filter');
  await page.locator('#foli-review').click(); await page.locator('#foli-progress').waitFor({state: 'visible'});
  await page.locator('#foli-stop').click(); await waitIdle();
  assert.match(await page.locator('#foli-alert').textContent(), /stopped/); pass('Real review request can be stopped');
  await select(data.documents['scan.pdf'].title);
  assert.match(await page.locator('#foli-coverage-summary').textContent(), /OCR/);
  await page.locator('#foli-source-open').click(); await page.locator('#foli-source-status').filter({hasText: /OCR/}).waitFor();
  await page.keyboard.press('Escape'); pass('Real scanned PDF shows OCR provenance and uncertainty');
  await select(data.documents['unsupported.docx'].title);
  assert.match(await page.locator('#foli-alert').textContent(), /not supported/); pass('Unsupported format is explicit');
  await page.locator('#foli-general').click(); await waitIdle();
  // Explicit synthetic model-response test for the browser trust boundary.
  const fakeId = 'e1c2a3b4-00aa-44cc-88dd-112233445566';
  const hostile = '<img src=x onerror=window.__foliXss=1> <script>window.__foliXss=2</script> [link](https://evil.invalid)';
  await page.route('**/ask-foli/api/jobs/', route => route.fulfill({status: 202, json: {id: fakeId, state: 'QUEUED', stage: 'Checking'}}));
  await page.route('**/ask-foli/api/jobs/' + fakeId + '/', route => route.fulfill({status: 200, json: {id: fakeId, state: 'COMPLETE', result: {
    answer: hostile, answerKind: 'GENERAL', citations: [], warnings: [], findings: [], performance: {}}}}));
  await ask('Display this synthetic browser safety case.');
  assert.equal(await page.evaluate(() => window.__foliXss), undefined);
  assert.equal(await page.locator('#foli-log img, #foli-log script, #foli-log a').count(), 0);
  assert((await page.locator('#foli-log').textContent()).includes(hostile));
  await page.unroute('**/ask-foli/api/jobs/'); await page.unroute('**/ask-foli/api/jobs/' + fakeId + '/');
  pass('Synthetic hostile model HTML/links render solely as text');
  await page.route('**/ask-foli/api/health/', route => route.fulfill({status: 200, json: {
    ollama: {status: 'MODEL_MISSING', model: 'test-missing'}, ocr: 'local', historyPersisted: false}}));
  await page.locator('#foli-health').click(); await page.locator('#foli-health-label').filter({hasText: 'Model not installed'}).waitFor();
  await page.unroute('**/ask-foli/api/health/'); pass('Synthetic missing-model state is clear');
  await page.locator('#foli-clear').click(); await waitIdle();
  await page.locator('#foli-alert').filter({hasText: 'This conversation was cleared'}).waitFor();
  assert.equal(await page.locator('#foli-log').textContent(), ''); pass('Explicit clear removes the current visible conversation');
  await page.setViewportSize({width: 390, height: 844}); await page.reload();
  await page.locator('#foli-documents .foli-doc').first().waitFor();
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  await page.screenshot({path: path.join(OUT, 'ui-mobile.png'), fullPage: true}); pass('390px mobile layout has no horizontal overflow');
  await page.locator('[data-theme-choice=dark]').first().click();
  assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
  await page.waitForFunction(() => !document.documentElement.classList.contains('theme-changing') && getComputedStyle(document.body).backgroundColor === 'rgb(21, 23, 26)');
  await page.screenshot({path: path.join(OUT, 'ui-mobile-dark.png'), fullPage: true}); pass('Existing dark theme works at 390px');
  await page.route('**/ask-foli/api/health/', route => route.fulfill({status: 401, json: {code: 'SIGNED_OUT', message: 'Sign in again.'}}));
  await page.locator('#foli-health').click();
  await page.locator('#foli-document-title').filter({hasText: 'Signed out'}).waitFor();
  assert.equal(await page.locator('#foli-log').textContent(), '');
  assert.equal(await page.locator('#foli-documents .foli-doc').count(), 0); pass('Synthetic authorization loss clears source and conversation data');
  assert.equal(errors.length, 0, errors.join('\n')); assert.equal(external.length, 0, external.join('\n'));
  pass('No browser JavaScript exceptions or external requests');
  const originals = await backend('/api/wallet/documents', data.auth);
  assert.equal(originals.length, 4); assert(originals.every(d => d.status === 'DRAFT')); pass('Original workflow state remains unchanged by reading/review/cancellation');
}
(async () => {
  let failure;
  try { await main(); }
  catch (error) { failure = {message: error.message, stack: error.stack}; console.error(error); if (page) await page.screenshot({path: path.join(OUT, 'ui-failure.png'), fullPage: true}).catch(() => {}); }
  finally {
    fs.writeFileSync(path.join(OUT, 'phase-4-ui.json'), JSON.stringify({browser: browser && browser.version(), events, errors, external, failure}, null, 2));
    if (browser) await browser.close(); if (failure) process.exitCode = 1;
  }
})();
