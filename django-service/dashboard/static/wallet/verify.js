document.addEventListener('DOMContentLoaded', () => {
  const bundle=JSON.parse(document.getElementById('proof-bundle').textContent);
  const output=document.getElementById('independent-result'),policy=document.getElementById('policy-result');
  const button=document.getElementById('verify-independent');
  const inputs=['rpc-url','expected-contract','expected-operator','expected-chain'].map(id=>document.getElementById(id));
  // Ledger cells are presentation only; the notices above remain the authoritative result text.
  const browserCells=typeof document.querySelectorAll==='function'?[...document.querySelectorAll('[data-browser-check]')]:[];
  const policyCell=document.getElementById('policy-cell'),summary=document.getElementById('ledger-summary');
  const say=text=>{if(summary)summary.textContent=text;};
  const mark=(cell,tone,text)=>{if(cell){cell.className='mark '+tone+(tone==='quiet'?'':' just-set');cell.textContent=text;}};
  const resetLedger=()=>{say('Your browser has not run its own check for these settings.');browserCells.forEach(cell=>mark(cell,'quiet','Not run'));mark(policyCell,'quiet','Not run');};
  for(const input of inputs)input.addEventListener('input',()=>{
    output.className='notice';output.textContent='Independent check not run for these settings.';policy.textContent='';policy.className='small muted';resetLedger();
  });
  document.getElementById('proof-details').textContent=JSON.stringify(bundle,null,2);
  button.addEventListener('click',async event=>{
    event.target.disabled=true;event.target.setAttribute?.('aria-busy','true');inputs.forEach(input=>input.disabled=true);
    output.className='notice';output.textContent='Recomputing facts and reading the registry…';policy.textContent='';policy.className='small muted';resetLedger();
    let provider;
    try{
      const rpc=new URL(document.getElementById('rpc-url').value);if(!['http:','https:'].includes(rpc.protocol))throw Error('Use an HTTP or HTTPS RPC endpoint.');
      provider=new ethers.JsonRpcProvider(rpc.href,undefined,{batchMaxCount:1});
      await ProofTools.verifyChain(bundle,provider,{contract:document.getElementById('expected-contract').value,
        operator:document.getElementById('expected-operator').value,chainId:document.getElementById('expected-chain').value});
      output.className='notice success';output.textContent='Independent cryptographic check passed: membership, platform signature and pinned on-chain credential state match. Holder authorization remains a custodial service decision.';
      browserCells.forEach(cell=>mark(cell,'pass','Passed'));say('This browser independently confirmed the five cryptographic and chain checks.');
      try {
        const response=await fetch('/proof-status/'+encodeURIComponent(bundle.presentation.grantId)+'/',{cache:'no-store'});
        if(!response.ok)throw Error('Service policy status is unavailable.');
        const state=await response.json();
        if(!state||!['ACTIVE','CONSUMED','REVOKED','EXPIRED','CREDENTIAL_UNAVAILABLE'].includes(state.status))throw Error('Malformed service policy status.');
        policy.textContent='Service-reported link status: '+state.status+'. Authorization/policy is custodial, not independently proven. Retained facts cannot be erased.';
        const closed=['REVOKED','EXPIRED','CREDENTIAL_UNAVAILABLE'].includes(state.status);
        if(closed){policy.className='notice warning';}
        mark(policyCell,closed?'fail':'caution','Service reports '+state.status.toLowerCase().replace('_',' '));
      } catch(error) {policy.className='notice warning';policy.textContent='Service policy unverified: '+error.message;mark(policyCell,'caution','Unverified');}
    }catch(error){output.className='notice error';output.textContent='Independent acceptance failed: '+error.message;browserCells.forEach(cell=>mark(cell,'fail','Not accepted'));say('This browser did not accept the proof: '+error.message);}
    finally{provider?.destroy();event.target.disabled=false;event.target.removeAttribute?.('aria-busy');inputs.forEach(input=>input.disabled=false);}
  });
});
