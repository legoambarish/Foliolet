const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.resolve(__dirname,'../../django-service/dashboard/static/wallet/verify.js'),'utf8');
function ui({cryptoFails=false,status={status:'ACTIVE'},policyFails=false}={}) {
  const ids=['proof-bundle','independent-result','policy-result','proof-details','verify-independent','rpc-url','expected-contract','expected-operator','expected-chain'];
  const elements=Object.fromEntries(ids.map(id=>[id,{textContent:'',value:'',listeners:{},addEventListener(event,fn){this.listeners[event]=fn;}}]));
  elements['proof-bundle'].textContent=JSON.stringify({presentation:{grantId:'fixture'}});
  elements['rpc-url'].value='http://127.0.0.1:8545';
  let fetched=false;
  vm.runInNewContext(source,{URL,document:{getElementById:id=>elements[id],addEventListener:(_,fn)=>fn()},
    ethers:{JsonRpcProvider:class{destroy(){}}},
    ProofTools:{async verifyChain(){if(cryptoFails)throw Error('Pin mismatch');}},
    fetch:async()=>{fetched=true;if(policyFails)throw Error('Unavailable');return {ok:true,json:async()=>status};}});
  return {elements,fetched:()=>fetched,click:()=>elements['verify-independent'].listeners.click({target:elements['verify-independent']})};
}
test('failed independent proof never becomes successful or queries policy',async()=>{
  const u=ui({cryptoFails:true});await u.click();
  assert.equal(u.elements['independent-result'].className,'notice error');assert.equal(u.fetched(),false);
});
test('malformed and unavailable service status remain separate from independent cryptography',async()=>{
  for(const options of [{status:{}},{status:null},{policyFails:true}]){
    const u=ui(options);await u.click();
    assert.equal(u.elements['independent-result'].className,'notice success');
    assert.match(u.elements['policy-result'].textContent,/Service policy unverified/);
  }
});
test('revoked service status is visibly separate from cryptographic membership',async()=>{
  const u=ui({status:{status:'REVOKED'}});await u.click();
  assert.equal(u.elements['independent-result'].className,'notice success');
  assert.equal(u.elements['policy-result'].className,'notice warning');
});
test('edited pins invalidate previously shown independent success',async()=>{
  const u=ui();await u.click();u.elements['expected-operator'].listeners.input();
  assert.equal(u.elements['independent-result'].className,'notice');
  assert.match(u.elements['independent-result'].textContent,/not run/);
});
