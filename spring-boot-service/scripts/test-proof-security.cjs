const {test}=require('node:test');
const assert=require('node:assert/strict');
const E=require('ethers');
const factory=require('../../django-service/dashboard/static/wallet/proof-core.js');
const tools=factory(E);
const wallet=E.Wallet.createRandom();
const hex=n=>'0x'+n.repeat(32);
async function fixture(change=()=>{}) {
  const now=Math.floor(Date.now()/1000)*1000;
  const b={format:tools.FORMAT,credentialId:hex('11'),credentialVersion:1,leafCount:1,
    anchor:{contract:'0x'+'22'.repeat(20),operator:wallet.address,chainId:1337,
      documentCommitment:hex('33'),anchoredAt:new Date(now-60000).toISOString(),provenanceCode:0,txHash:null},
    provenance:{level:'SELF_ENROLLED',explanation:'Holder confirmed',firstReceivedAt:null,lastReceivedAt:null,
      observations:0,observedChanges:false,enrollmentMatchesFirst:false,agentId:null},
    presentation:{grantId:'11111111-1111-4111-8111-111111111111',verifierLabel:'Desk',purpose:'Eligibility',nonce:hex('44'),
      createdAt:new Date(now-1000).toISOString(),expiresAt:new Date(now+60000).toISOString(),oneTime:false},
    claims:[{leaf:{path:'education.cgpa',label:'CGPA',type:'decimal',value:'9.17',derivedFrom:'',salt:hex('55'),index:0},proof:[]}]};
  change(b);
  b.merkleRoot=tools.leafHash(b.claims[0].leaf);
  b.anchor.provenanceDigest=tools.provenanceHash(b.provenance);
  b.envelopeHash=tools.envelopeHash(b);
  b.platformSignature=await wallet.signMessage(E.getBytes(b.envelopeHash));
  return b;
}
function chain(b) {
  let calls=0;
  const verifier=factory({...E,Contract:class {
    async operator(){return b.anchor.operator;}
    async getCredential(){return [b.merkleRoot,b.anchor.documentCommitment,b.anchor.provenanceDigest,b.anchor.operator,
      BigInt(Date.parse(b.anchor.anchoredAt)/1000),1n,0n,1n,hex('00')];}
  }});
  return {verifier,provider:{async getNetwork(){calls++;return {chainId:1337n};}},calls:()=>calls};
}
test('genuine cryptography and separately supplied deployment pins pass',async()=>{
  const b=await fixture(),c=chain(b);
  assert.equal((await c.verifier.verifyChain(b,c.provider,{...b.anchor})).current,true);
});
test('all deployment pins are mandatory before any RPC',async()=>{
  const b=await fixture();
  for(const pins of [undefined,{}, {contract:b.anchor.contract}, {contract:b.anchor.contract,chainId:1337},
    {...b.anchor,operator:''}, {...b.anchor,contract:'0x'+'00'.repeat(20)}, {...b.anchor,chainId:'1e3'},
    {...b.anchor,chainId:true}, {...b.anchor,operator:'malformed'}]) {
    const c=chain(b);
    await assert.rejects(()=>c.verifier.verifyChain(b,c.provider,pins));
    assert.equal(c.calls(),0);
  }
});
test('untrusted deployment cannot replace independently configured pins',async()=>{
  const b=await fixture(),c=chain(b);
  await assert.rejects(()=>c.verifier.verifyChain(b,c.provider,{...b.anchor,operator:'0x'+'ab'.repeat(20)}));
  await assert.rejects(()=>c.verifier.verifyChain(b,c.provider,{...b.anchor,contract:'0x'+'ab'.repeat(20)}));
  await assert.rejects(()=>c.verifier.verifyChain(b,c.provider,{...b.anchor,chainId:1}));
});
for(const [name,change] of Object.entries({
  'unsupported type': b=>b.claims[0].leaf.type='invented',
  'noncanonical decimal': b=>b.claims[0].leaf.value='9.170',
  'invalid path': b=>b.claims[0].leaf.path='Education.CGPA',
  'noncanonical label': b=>b.claims[0].leaf.label=' CGPA ',
  'control label': b=>b.claims[0].leaf.label='CGPA\u0085',
  'non NFC text': b=>Object.assign(b.claims[0].leaf,{type:'string',value:'e\u0301'}),
  'invalid date': b=>Object.assign(b.claims[0].leaf,{type:'date',value:'2026-02-30'}),
  'noncanonical boolean': b=>Object.assign(b.claims[0].leaf,{type:'boolean',value:'TRUE'}),
  'string boolean': b=>b.presentation.oneTime='false',
  'string chain ID': b=>b.anchor.chainId='1337',
  'string provenance count': b=>b.provenance.observations='0',
  'string provenance boolean': b=>b.provenance.observedChanges='false',
})) test('rejects correctly signed but malformed '+name,async()=>{
  const b=await fixture(change);
  assert.throws(()=>tools.verifyCryptography(b));
});
test('altered fact still fails',async()=>{
  const b=await fixture();b.claims[0].leaf.value='8.17';assert.throws(()=>tools.verifyCryptography(b));
});
test('unsigned unknown fields cannot be included as authenticated content',async()=>{
  for(const location of ['top','anchor','leaf']) {
    const b=await fixture();
    const target=location==='top'?b:location==='anchor'?b.anchor:b.claims[0].leaf;
    target.unsignedExtra='not authenticated';
    assert.throws(()=>tools.verifyCryptography(b));
  }
});
test('shared Java canonical value vectors agree',async()=>{
  const rows=require('../src/test/resources/canonical-vectors.json');
  for(const row of rows) {
    const b=await fixture(b=>Object.assign(b.claims[0].leaf,{type:row.type,value:row.value}));
    if(row.valid)assert.equal(tools.verifyCryptography(b).proofValid,true,JSON.stringify(row));
    else assert.throws(()=>tools.verifyCryptography(b),undefined,JSON.stringify(row));
  }
});
