document.addEventListener('DOMContentLoaded', () => {
  const bundle=JSON.parse(document.getElementById('proof-bundle').textContent);
  const output=document.getElementById('independent-result'),policy=document.getElementById('policy-result');
  const inputs=['rpc-url','expected-contract','expected-operator','expected-chain'].map(id=>document.getElementById(id));
  for(const input of inputs)input.addEventListener('input',()=>{
    output.className='notice';output.textContent='Independent check not run for these settings.';policy.textContent='';
  });
  document.getElementById('proof-details').textContent=JSON.stringify(bundle,null,2);
  document.getElementById('verify-independent').addEventListener('click',async event=>{
    event.target.disabled=true;inputs.forEach(input=>input.disabled=true);
    output.className='notice';output.textContent='Recomputing facts and reading the registry…';policy.textContent='';policy.className='small muted';
    let provider;
    try{
      const rpc=new URL(document.getElementById('rpc-url').value);if(!['http:','https:'].includes(rpc.protocol))throw Error('Use an HTTP or HTTPS RPC endpoint.');
      provider=new ethers.JsonRpcProvider(rpc.href,undefined,{batchMaxCount:1});
      await ProofTools.verifyChain(bundle,provider,{contract:document.getElementById('expected-contract').value,
        operator:document.getElementById('expected-operator').value,chainId:document.getElementById('expected-chain').value});
      output.className='notice success';output.textContent='Independent cryptographic check passed: membership, platform signature and pinned on-chain credential state match. Holder authorization remains a custodial service decision.';
      try {
        const response=await fetch('/proof-status/'+encodeURIComponent(bundle.presentation.grantId)+'/',{cache:'no-store'});
        if(!response.ok)throw Error('Service policy status is unavailable.');
        const state=await response.json();
        if(!state||!['ACTIVE','CONSUMED','REVOKED','EXPIRED','CREDENTIAL_UNAVAILABLE'].includes(state.status))throw Error('Malformed service policy status.');
        policy.textContent='Service-reported link status: '+state.status+'. Authorization/policy is custodial, not independently proven. Retained facts cannot be erased.';
        if(['REVOKED','EXPIRED','CREDENTIAL_UNAVAILABLE'].includes(state.status)){policy.className='notice warning';}
      } catch(error) {policy.className='notice warning';policy.textContent='Service policy unverified: '+error.message;}
    }catch(error){output.className='notice error';output.textContent='Independent acceptance failed: '+error.message;}
    finally{provider?.destroy();event.target.disabled=false;inputs.forEach(input=>input.disabled=false);}
  });
});
