/* Real Edge upload -> source review -> confirmation -> EVM -> selective disclosure. Fictional data only. */
const {chromium}=require(process.env.FOLI_PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const ROOT=path.resolve(__dirname,'..'),OUT=path.join(ROOT,'.local-data','ocr-p0','walkthrough');
const UI='http://127.0.0.1:8008',API='http://127.0.0.1:8088',RPC='http://127.0.0.1:8548';
const checks=[],errors=[],external=[];let browser;
function pass(name){checks.push({name,result:'PASS'});console.log(new Date().toISOString(),'PASS',name);}
async function main(){
 fs.mkdirSync(OUT,{recursive:true});
 const auth=['ocr-ui-'+crypto.randomBytes(6).toString('hex'),'isolated-'+crypto.randomBytes(20).toString('hex')];
 const basic='Basic '+Buffer.from(auth.join(':')).toString('base64');
 let r=await fetch(API+'/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:auth[0],password:auth[1],role:'HOLDER'})});assert(r.ok);
 browser=await chromium.launch({headless:true,channel:process.env.FOLI_BROWSER_CHANNEL||'msedge'});
 const ctx=await browser.newContext({viewport:{width:1365,height:1000}});
 await ctx.route('**/*',async route=>{const u=route.request().url();if(![UI+'/',API+'/',RPC+'/','data:','blob:'].some(origin=>u.startsWith(origin))){external.push(u.split('/').slice(0,3).join('/'));await route.abort();}else await route.continue();});
 const page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto(UI+'/login/');await page.locator('#username').fill(auth[0]);await page.locator('#password').fill(auth[1]);
 await Promise.all([page.waitForURL(UI+'/'),page.getByRole('button',{name:'Sign in',exact:true}).click()]);
 async function upload(name){await page.goto(UI+'/wallet/enroll/');await page.locator('#file').setInputFiles(path.join(ROOT,'.local-data/ocr-p0/fixtures',name+'.pdf'));await page.locator('#name').fill('Fictional semester report — '+name);await Promise.all([page.waitForURL(/\/wallet\/0x[0-9a-f]{64}\//),page.getByRole('button',{name:'Upload and review facts',exact:true}).click()]);return page.url().split('/').filter(Boolean).at(-1);}
 const id=await upload('native-table');
 await page.waitForFunction(()=>[...document.querySelectorAll('[name=claim_label]')].filter(e=>e.value).length===19,null,{timeout:180000});
 let status=await fetch(API+'/api/wallet/intake/documents/'+id,{headers:{Authorization:basic}}).then(r=>r.json());
 assert.equal(status.report.diagnostics.supported,19);assert.equal(status.issuer,'NOT_VERIFIED');
 const math=page.locator('.edit-row').filter({has:page.locator('[name=claim_path][value="education.math"]')});
 // JS property updates do not need to change attributes; find by live field values.
 const index=await page.locator('[name=claim_path]').evaluateAll(nodes=>nodes.findIndex(n=>n.value==='education.math'));
 const row=page.locator('.edit-row').nth(index);assert.equal(await row.locator('[name=claim_value]').inputValue(),'91');
 await row.locator('summary').filter({hasText:'Source evidence'}).click();assert.match(await row.locator('details').last().innerText(),/Mathematics/);
 const original=await ctx.request.get(UI+await row.locator('.scan-note a').getAttribute('href'));assert.equal(original.status(),200);assert.match(original.headers()['content-type'],/image\/png/);
 await page.screenshot({path:path.join(OUT,'01-table-review.png'),fullPage:true});
 pass('Realistic five-subject marksheet yields 19 exact source-supported facts with original-page preview');
 await page.locator('[name=confirm]').check();await Promise.all([page.waitForNavigation(),page.getByRole('button',{name:'Confirm facts',exact:true}).click()]);
 status=await fetch(API+'/api/wallet/intake/documents/'+id,{headers:{Authorization:basic}}).then(r=>r.json());assert.equal(status.lineage,'SUGGESTIONS_UNMODIFIED');
 await Promise.all([page.waitForNavigation(),page.getByRole('button',{name:'Anchor commitment',exact:true}).click()]);
 await page.getByRole('link',{name:'Share a proof',exact:true}).click();
 await page.locator('.choice').filter({hasText:'Mathematics marks'}).filter({hasNotText:'maximum'}).locator('[name=claims]').check();
 assert.equal(await page.locator('[name=claims]:checked').count(),1);
 await page.locator('#verifier').fill('Fictional internship reviewer');await page.locator('#purpose').fill('PS32 local extraction regression');
 await page.getByRole('button',{name:'Create proof link',exact:true}).click();await page.locator('#share-url').waitFor();
 const link=await page.locator('#share-url').inputValue();await page.goto(link.replace('http://localhost:8008',UI));
 await page.getByRole('button',{name:'Open disclosed facts',exact:true}).click();await page.getByRole('heading',{name:'1 fact disclosed to you',exact:true}).waitFor();
 await page.locator('#verify-independent').click();await page.waitForFunction(()=>document.getElementById('independent-result').textContent.includes('Independent cryptographic check passed'),null,{timeout:30000});
 assert(!await page.locator('.slip').innerText().then(t=>t.includes('Ananya Rao')));assert.match(await page.locator('.slip').innerText(),/91/);
 await page.screenshot({path:path.join(OUT,'02-selective-disclosure.png'),fullPage:true});
 pass('Holder confirms all facts, anchors, shares only Mathematics 91; independent browser verifies the chain proof');
 await upload('scan-table');await page.waitForFunction(()=>document.querySelectorAll('.use-reviewed-fact').length===19,null,{timeout:180000});
 assert.equal(await page.locator('[name=claim_value]').first().inputValue(),'');
 await page.screenshot({path:path.join(OUT,'03-scanned-review.png'),fullPage:true});
 const card=page.locator('#intake-review .notice').filter({hasText:'Mathematics marks: 91'});assert.equal(await card.count(),1);await card.getByRole('button',{name:'Use after checking'}).click();
 assert.equal(await page.locator('[name=claim_value]').first().inputValue(),'91');
 pass('Scanned table has 19 review cards and no automatically accepted facts; explicit checking adds one editable value');
 await page.locator('[name=claim_value]').first().fill('95');await page.locator('[name=confirm]').check();await Promise.all([page.waitForNavigation(),page.getByRole('button',{name:'Confirm facts',exact:true}).click()]);
 await page.getByText('Facts edited since extraction',{exact:true}).first().waitFor();
 pass('Changing scanned Mathematics 91 to 95 is recorded server-side as an edit');
 assert.equal(errors.length,0,JSON.stringify(errors));assert.equal(external.length,0,JSON.stringify(external));
 pass('Walkthrough had no JavaScript errors or document requests outside loopback');
 fs.writeFileSync(path.join(OUT,'results.json'),JSON.stringify({checks,count:checks.length,fictional:true},null,2));
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
