/* Same bounded evaluator is used by the browser and the standalone Node reader. */
(function(root,factory){if(typeof module==='object'&&module.exports){const E=require('./vendor/ethers.umd.min.js');module.exports=factory(E,require('./proof-core.js')(E));}else root.FolioletBridge=factory(root.ethers,root.ProofTools);})(typeof globalThis!=='undefined'?globalThis:this,function(E,M){
 'use strict';
 const ABI=[
 'function governance() view returns(address)',
 'function issuers(address) view returns(string name,bool recognized,bool suspended,uint64 changedBlock)',
 'function scopes(address,bytes32) view returns(bool)',
 'function getEvidence(bytes32) view returns(tuple(bytes32 root,bytes32 documentCommitment,bytes32 claimType,address issuer,address holder,uint32 leafCount,uint32 version,uint64 issuedAt,uint64 expiresAt,uint64 anchorBlock,uint64 changedBlock,uint8 evidenceClass,uint8 status,bytes32 supersededBy))'];
 const TYPES={
 Request:[{name:'requestHash',type:'bytes32'}],
 Presentation:[{name:'requestHash',type:'bytes32'},{name:'credentialId',type:'bytes32'},{name:'disclosuresHash',type:'bytes32'},{name:'nonce',type:'bytes32'},{name:'verifier',type:'address'},{name:'expiresAt',type:'uint64'}],
 Decision:[{name:'bundleHash',type:'bytes32'},{name:'decisionHash',type:'bytes32'},{name:'blockHash',type:'bytes32'},{name:'readBlock',type:'uint64'}],
 PlanApproval:[{name:'planHash',type:'bytes32'},{name:'requestHash',type:'bytes32'},{name:'nonce',type:'bytes32'},{name:'expiresAt',type:'uint64'}]
 };
 const CLAIMS={
 'internship-eligibility/v1':{'education.cgpa_at_least_8_5':['boolean','CGPA at least 8.5','education.cgpa'],'education.enrolled':['boolean','Currently enrolled',''],'subject.name':['string','Name','']},
 'income-evidence/v1':{'employment.monthly_income':['decimal','Monthly income',''],'employment.currency':['string','Currency',''],'employment.active':['boolean','Employment active',''],'subject.name':['string','Name','']}
 };
 function stable(v){if(v===null||typeof v==='string'||typeof v==='boolean')return JSON.stringify(v);if(typeof v==='number'){if(!Number.isSafeInteger(v))throw Error('Only safe integers in protocol metadata');return String(v);}if(Array.isArray(v))return '['+v.map(stable).join(',')+']';if(typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+stable(v[k])).join(',')+'}';throw Error('Unsupported JSON value');}
 const digest=v=>E.keccak256(E.toUtf8Bytes(stable(v)));
 const domain=p=>({name:'FolioletEvidenceBridge',version:'1',chainId:p.chainId,verifyingContract:p.registry});
 const eq=(a,b)=>typeof a==='string'&&typeof b==='string'&&a.toLowerCase()===b.toLowerCase();
 const hex=v=>typeof v==='string'&&/^0x[0-9a-fA-F]{64}$/.test(v);
 function keys(v,fields){if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).sort().join('|')!==fields.slice().sort().join('|'))throw Error('Unexpected schema fields');}
 function integer(n,min,max){if(!Number.isSafeInteger(n)||n<min||n>max)throw Error('Invalid bounded integer');}
 function validateRequest(r){
  keys(r,['id','verifier','purpose','retentionDays','claims','nonce','issuedAt','expiresAt','policy']);
  if(!hex(r.id)||!hex(r.nonce)||!E.isAddress(r.verifier))throw Error('Invalid request identity');
  if(typeof r.purpose!=='string'||r.purpose.trim()!==r.purpose||r.purpose.length<3||r.purpose.length>240)throw Error('Invalid purpose');
  integer(r.issuedAt,1,Number.MAX_SAFE_INTEGER);integer(r.expiresAt,r.issuedAt+1,r.issuedAt+604800);integer(r.retentionDays,0,30);
  if(!Array.isArray(r.claims)||r.claims.length<1||r.claims.length>8||new Set(r.claims).size!==r.claims.length||r.claims.some(x=>typeof x!=='string'))throw Error('Invalid requested claims');
  keys(r.policy,['claimType','acceptedIssuers','evidenceClasses','maxReadAgeSeconds','holderBinding','requiredValues','minimumValues']);
  const p=r.policy;if(!CLAIMS[p.claimType]||r.claims.some(c=>!CLAIMS[p.claimType][c]))throw Error('Unsupported typed policy');
  if(!Array.isArray(p.acceptedIssuers)||p.acceptedIssuers.length<1||p.acceptedIssuers.length>8||p.acceptedIssuers.some(x=>!E.isAddress(x)))throw Error('Invalid accepted issuers');
  if(stable(p.evidenceClasses)!=='[2]'||p.holderBinding!==true)throw Error('Issuer evidence and holder binding required');
  integer(p.maxReadAgeSeconds,1,300);
  for(const map of [p.requiredValues,p.minimumValues]){if(!map||Array.isArray(map)||typeof map!=='object'||Object.keys(map).some(k=>!r.claims.includes(k)))throw Error('Unrequested policy field');}
  for(const [path,value] of Object.entries(p.requiredValues)){if(typeof value!=='string'||value.length>240)throw Error('Invalid predicate');}
  for(const [path,value] of Object.entries(p.minimumValues)){if(CLAIMS[p.claimType][path][0]!=='decimal'||typeof value!=='string'||!/^\d+(\.\d+)?$/.test(value)||value.length>20)throw Error('Invalid minimum');}
  return digest(r);
 }
 function presentation(b){return{requestHash:validateRequest(b.request),credentialId:b.credential.id,disclosuresHash:E.keccak256(E.concat(b.claims.map(c=>M.leafHash(c.leaf)))),nonce:b.request.nonce,verifier:b.request.verifier,expiresAt:b.request.expiresAt};}
 function validateBundle(b){
  keys(b,['format','registry','chainId','credential','request','requestSignature','claims','holderSignature']);if(b.format!=='foliolet-evidence-bridge-v1')throw Error('Unsupported format');
  integer(b.chainId,1,Number.MAX_SAFE_INTEGER);if(!E.isAddress(b.registry))throw Error('Invalid registry');validateRequest(b.request);
  keys(b.credential,['id','root','documentCommitment','claimType','issuer','holder','leafCount','version','evidenceClass','expiresAt']);
  const c=b.credential;for(const field of ['id','root','documentCommitment'])if(!hex(c[field]))throw Error('Invalid commitment');
  if(!E.isAddress(c.issuer)||!E.isAddress(c.holder)||!CLAIMS[c.claimType])throw Error('Invalid evidence metadata');
  integer(c.leafCount,1,128);integer(c.version,1,1000000);integer(c.expiresAt,1,Number.MAX_SAFE_INTEGER);integer(c.evidenceClass,0,255);
  if(!Array.isArray(b.claims)||b.claims.length!==b.request.claims.length||b.claims.length>8)throw Error('Exact requested subset required');
  const seen=new Set(),indices=new Set();for(const claim of b.claims){keys(claim,['leaf','proof']);keys(claim.leaf,['path','label','type','value','derivedFrom','salt','index']);const l=claim.leaf,s=CLAIMS[c.claimType][l.path];
   if(!s||s[0]!==l.type||s[1]!==l.label||s[2]!==l.derivedFrom||!b.request.claims.includes(l.path)||seen.has(l.path)||indices.has(l.index))throw Error('Typed claim semantics mismatch');
   seen.add(l.path);indices.add(l.index);if(typeof l.value!=='string'||l.value.length>240||l.value!==l.value.normalize('NFC').trim()||/[\u0000-\u001f\u007f]/.test(l.value))throw Error('Noncanonical value');
   if(l.type==='boolean'&&!['true','false'].includes(l.value))throw Error('Invalid boolean');if(l.type==='decimal'&&!/^(0|[1-9]\d*)(\.\d*[1-9])?$/.test(l.value))throw Error('Noncanonical decimal');
   integer(l.index,0,c.leafCount-1);if(!hex(l.salt)||!Array.isArray(claim.proof)||claim.proof.length>7)throw Error('Invalid proof');for(const step of claim.proof){keys(step,['sibling','side']);if(!hex(step.sibling)||!['LEFT','RIGHT'].includes(step.side))throw Error('Invalid proof step');}
  }
  for(const signature of [b.requestSignature,b.holderSignature])if(typeof signature!=='string'||!/^0x[0-9a-fA-F]{130}$/.test(signature))throw Error('Invalid signature');
  return b;
 }
 async function verify(b,pins,options={}){
  const ledger=[];const add=(requirement,status,reason)=>ledger.push({requirement,status,reason});let block;
  try{validateBundle(b);add('schema','PASS','Bounded typed package');}catch(e){add('schema','FAIL',e.message);return {result:'FAIL',ledger,mode:options.mode||'current'};}
  const c=b.credential,r=b.request;
  if(!pins||!E.isAddress(pins.registry)||!E.isAddress(pins.governance)||!Number.isSafeInteger(pins.chainId)||!hex(pins.codeHash)){add('trust','UNKNOWN','External registry, governance, chain and code pins required');return{result:'UNKNOWN',ledger,mode:options.mode||'current'};}
  add('deployment',eq(b.registry,pins.registry)&&b.chainId===pins.chainId?'PASS':'FAIL','Package must match independently provisioned registry and chain');
  const trustedVerifier=options.verifier||pins.verifiers?.find(x=>eq(x,r.verifier))||pins.actors?.slice(6,8).find(x=>eq(x.address,r.verifier))?.address;
  add('verifier identity',eq(trustedVerifier,r.verifier)?'PASS':'FAIL','Expected recipient must come from external configuration');
  try{add('signed request',eq(E.verifyTypedData(domain(pins),{Request:TYPES.Request},{requestHash:digest(r)},b.requestSignature),r.verifier)?'PASS':'FAIL','Verifier signs complete purpose, retention, policy, nonce and deadline');}catch(e){add('signed request','FAIL',e.message);}
  try{add('holder authorization',eq(E.verifyTypedData(domain(pins),{Presentation:TYPES.Presentation},presentation(b),b.holderSignature),c.holder)?'PASS':'FAIL','Holder signs exact disclosed commitments and request context');}catch(e){add('holder authorization','FAIL',e.message);}
  try{add('Merkle membership',b.claims.every(x=>M.verifyPath(x.leaf,x.proof,c.leafCount,c.root))?'PASS':'FAIL','Each typed claim belongs to the anchored root');}catch(e){add('Merkle membership','FAIL',e.message);}
  const policy=r.policy;
  add('evidence policy',c.claimType===policy.claimType&&policy.acceptedIssuers.some(x=>eq(x,c.issuer))&&policy.evidenceClasses.includes(c.evidenceClass)?'PASS':'FAIL','Requested issuer, type and source class');
  const values=Object.fromEntries(b.claims.map(x=>[x.leaf.path,x.leaf.value]));
  const minimum=(value,bound)=>{if(!/^\d+(\.\d+)?$/.test(value))return false;const scale=Math.max((value.split('.')[1]||'').length,(bound.split('.')[1]||'').length);const n=s=>BigInt(s.replace('.','').padEnd(s.split('.')[0].length+scale,'0'));return n(value)>=n(bound);};
  add('typed predicates',Object.entries(policy.requiredValues).every(([k,v])=>values[k]===v)&&Object.entries(policy.minimumValues).every(([k,v])=>minimum(values[k],v))?'PASS':'FAIL','Only disclosed typed values are evaluated; no AI or hidden range inference');
  try{
   const provider=options.provider||new E.JsonRpcProvider(options.rpc||pins.rpc);const network=await provider.getNetwork();if(Number(network.chainId)!==pins.chainId)throw Error('Wrong RPC chain');
   block=await provider.getBlock(options.mode==='historical'?options.readBlock:'latest');if(!block)throw Error('Read block unavailable');
   if(options.mode==='historical'&&!Number.isSafeInteger(options.readBlock))throw Error('Explicit saved block required');
   if(options.blockHash&&!eq(options.blockHash,block.hash))throw Error('Saved read block hash differs');
   if(E.keccak256(await provider.getCode(pins.registry,block.number))!==pins.codeHash)throw Error('Pinned registry code mismatch');
   const contract=new E.Contract(pins.registry,ABI,provider),at={blockTag:block.number};
   add('governance root',eq(await contract.governance(at),pins.governance)?'PASS':'FAIL','Immutable governance root matches external pin');
   const [record,issuer,scoped]=await Promise.all([contract.getEvidence(c.id,at),contract.issuers(c.issuer,at),contract.scopes(c.issuer,E.id(c.claimType),at)]);
   const matches=eq(record.root,c.root)&&eq(record.documentCommitment,c.documentCommitment)&&eq(record.claimType,E.id(c.claimType))&&eq(record.issuer,c.issuer)&&eq(record.holder,c.holder)&&Number(record.leafCount)===c.leafCount&&Number(record.version)===c.version&&Number(record.evidenceClass)===c.evidenceClass&&Number(record.expiresAt)===c.expiresAt;
   add('anchor',''+(matches?'PASS':'FAIL'),'Immutable on-chain evidence fields match package');
   add('issuer authority',issuer.recognized&&!issuer.suspended&&scoped?'PASS':'FAIL','Recognized, unsuspended issuer is scoped for this type at the read block');
   add('credential lifecycle',Number(record.status)===1&&Number(record.expiresAt)>block.timestamp?'PASS':'FAIL','Active, unexpired and not superseded or revoked at the read block');
   const now=options.now??Math.floor(Date.now()/1000),evaluationTime=options.mode==='historical'?options.decisionAt:now;
   integer(evaluationTime,1,Number.MAX_SAFE_INTEGER);
   add('request window',r.issuedAt<=evaluationTime&&evaluationTime<r.expiresAt?'PASS':'FAIL','Signed verifier request is within its authorization window');
   add('freshness',block.timestamp<=evaluationTime+30&&evaluationTime-block.timestamp<=policy.maxReadAgeSeconds?'PASS':'UNKNOWN','Read age is bounded by signed policy and trusted local clock');
   add('source truth','UNKNOWN','Test issuer attestation is accountable evidence, not independent proof that the real-world facts are true');
   return{result:ledger.some(x=>x.status==='FAIL')?'FAIL':ledger.filter(x=>x.requirement!=='source truth').some(x=>x.status==='UNKNOWN')?'UNKNOWN':'PASS',mode:options.mode||'current',ledger,readBlock:block.number,blockHash:block.hash,blockTimestamp:block.timestamp,anchorBlock:Number(record.anchorBlock),lastChangeBlock:Math.max(Number(record.changedBlock),Number(issuer.changedBlock)),decisionAt:evaluationTime,bundleHash:digest(b)};
  }catch(e){add('chain read','UNKNOWN',e.message);return{result:ledger.some(x=>x.status==='FAIL')?'FAIL':'UNKNOWN',mode:options.mode||'current',ledger};}
 }
 function receiptOptions(receipt,bundle,pins){
  keys(receipt,['format','evaluation','decisionHash','signature','verifier','bundle']);
  if(receipt.format!=='foliolet-decision-v1'||digest(receipt.bundle)!==digest(bundle)||receipt.evaluation.bundleHash!==digest(bundle)||digest(receipt.evaluation)!==receipt.decisionHash||!eq(receipt.verifier,bundle.request.verifier))throw Error('Saved decision package or evaluation differs');
  const e=receipt.evaluation;integer(e.readBlock,0,Number.MAX_SAFE_INTEGER);integer(e.decisionAt,1,Number.MAX_SAFE_INTEGER);if(!hex(e.blockHash))throw Error('Invalid saved block');
  const signed={bundleHash:digest(bundle),decisionHash:receipt.decisionHash,blockHash:e.blockHash,readBlock:e.readBlock};
  if(!eq(E.verifyTypedData(domain(pins),{Decision:TYPES.Decision},signed,receipt.signature),receipt.verifier))throw Error('Verifier decision signature differs');
  return{mode:'historical',readBlock:e.readBlock,blockHash:e.blockHash,decisionAt:e.decisionAt};
 }
 return{ABI,TYPES,CLAIMS,stable,digest,domain,validateRequest,validateBundle,presentation,verify,receiptOptions};
});
