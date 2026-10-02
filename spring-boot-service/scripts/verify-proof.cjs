const fs=require('node:fs');
const E=require('ethers');
const tools=require('../../django-service/dashboard/static/wallet/proof-core.js')(E);
async function main(){
  const args=process.argv.slice(2),file=args[0];
  const option=(name)=>{const i=args.indexOf(name);return i<0?null:args[i+1];};
  const contract=option('--contract'),rpc=option('--rpc')||'http://127.0.0.1:8545';
  if(!file||!contract)throw Error('Usage: node verify-proof.cjs BUNDLE.json --contract TRUSTED_REGISTRY --operator TRUSTED_OPERATOR --chain-id TRUSTED_CHAIN [--rpc URL]. Obtain all pins separately from the bundle and Spring service.');
  const pins=tools.trustPins({contract,operator:option('--operator'),chainId:option('--chain-id')});
  const bundle=JSON.parse(fs.readFileSync(file,'utf8'));const provider=new E.JsonRpcProvider(rpc,undefined,{batchMaxCount:1});
  try{
    const result=await tools.verifyChain(bundle,provider,pins);
    console.log(JSON.stringify({cryptographicVerification:result,sourceAssurance:bundle.provenance.level,
      servicePolicy:'Not checked by this offline-bundle tool. Query the live grant status for service revocation.',
      statement:'Cryptographic membership and pinned on-chain credential state. Holder disclosure authorization is enforced by the custodial service, not independently established against a malicious platform. First-seen tracking is limited continuity, not independent issuer authenticity. No document-truth or zero-knowledge claim.'},null,2));
  }finally{provider.destroy();}
}
main().catch(e=>{console.error('Verification failed: '+e.message);process.exitCode=1;});
