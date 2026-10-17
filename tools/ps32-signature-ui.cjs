/* Actual private browser flow. All documents and credentials are fictional. */
const {chromium}=require(process.env.FOLI_PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const ROOT=path.resolve(__dirname,'..'),UI='http://127.0.0.1:8008',API='http://127.0.0.1:8088';
let browser; const checks=[],external=[],errors=[];
async function main(){
 if(process.env.GITHUB_ACTIONS!=='true')throw Error('Use only the disposable CI environment');
 const fixture="from pathlib import Path; from dashboard.test_pdf_signatures import fictional_pdf,signed_fixture; p=Path('../.local-data/ps32-signature-fixtures'); p.mkdir(parents=True,exist_ok=True); s=signed_fixture(); (p/'unsigned.pdf').write_bytes(fictional_pdf()); (p/'signed.pdf').write_bytes(s); (p/'tampered.pdf').write_bytes(s.replace(b'91 marks',b'95 marks',1))";
 execFileSync('python',['manage.py','shell','-c',fixture],{cwd:path.join(ROOT,'django-service'),stdio:'pipe',timeout:30000});
 const auth=['signature-ui-'+crypto.randomBytes(6).toString('hex'),'fixture-'+crypto.randomBytes(20).toString('hex')];
 const response=await fetch(API+'/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:auth[0],password:auth[1],role:'HOLDER'})});assert(response.ok);
 browser=await chromium.launch({headless:true});const ctx=await browser.newContext({viewport:{width:1300,height:1000}});
 await ctx.route('**/*',async route=>{const u=route.request().url();if(![UI+'/',API+'/','data:','blob:'].some(o=>u.startsWith(o))){external.push(new URL(u).origin);await route.abort();}else await route.continue();});
 const page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto(UI+'/login/');await page.locator('#username').fill(auth[0]);await page.locator('#password').fill(auth[1]);
 await Promise.all([page.waitForURL(UI+'/'),page.getByRole('button',{name:'Sign in',exact:true}).click()]);
 for(const [name,status] of [['unsigned','UNSIGNED'],['signed','SIGNATURE_VALID_BUT_ISSUER_UNTRUSTED'],['tampered','SIGNATURE_OR_CURRENT_FILE_CHECK_FAILED']]){
  await page.goto(UI+'/wallet/enroll/');await page.locator('#file').setInputFiles(path.join(ROOT,'.local-data/ps32-signature-fixtures',name+'.pdf'));
  await page.locator('#name').fill('Fictional '+name+' PDF signature demonstration');
  await Promise.all([page.waitForURL(/\/wallet\/0x[0-9a-f]{64}\//),page.getByRole('button',{name:'Upload and review facts',exact:true}).click()]);
  await page.getByRole('button',{name:'Inspect PDF signature locally',exact:true}).waitFor({timeout:60000});
  await Promise.all([page.waitForNavigation(),page.getByRole('button',{name:'Inspect PDF signature locally',exact:true}).click()]);
  const text=await page.locator('main').innerText();
  assert(text.includes(status),name+': '+text.slice(0,1000));
  assert(text.includes('Issuer authenticity is not established'));
  const expected=crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT,'.local-data/ps32-signature-fixtures',name+'.pdf'))).digest('hex');
  assert(text.includes(expected),'Report source hash must match uploaded original');
  if(name==='signed')await page.screenshot({path:path.join(ROOT,'audit-evidence/signature-inspection.png'),fullPage:true});
  checks.push({case:name,result:'PASS',sourceHashMatched:true,issuerVerified:false});
 }
 assert.equal(errors.length,0,JSON.stringify(errors));assert.equal(external.length,0,JSON.stringify(external));
 fs.writeFileSync(path.join(ROOT,'audit-evidence/signature-ui-results.json'),JSON.stringify({checks,externalRequests:external.length,pageErrors:errors.length,fictional:true},null,2));
 console.log('PASS three real signature-inspection browser cases; zero external document requests');
}
main().catch(error=>{console.error(error.stack);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
