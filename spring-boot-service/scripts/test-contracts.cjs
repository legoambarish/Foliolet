const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ganache=require('ganache');
const E=require('ethers');
const proof=require('../../django-service/dashboard/static/wallet/proof-core.js')(E);
async function main(){
  // An isolated real in-memory EVM, not a mocked blockchain.
  const raw=ganache.provider({logging:{quiet:true},chain:{chainId:1337}}),provider=new E.BrowserProvider(raw);
  try{
    const signer=await provider.getSigner(0),other=await provider.getSigner(1);
    const dir=path.join(__dirname,'../src/main/resources/solidity/SelectiveDisclosureRegistry');
    const factory=new E.ContractFactory(JSON.parse(fs.readFileSync(path.join(dir,'SelectiveDisclosureRegistry.abi'))),fs.readFileSync(path.join(dir,'SelectiveDisclosureRegistry.bin'),'utf8').trim(),signer);
    const c=await factory.deploy();await c.waitForDeployment();const h=()=>E.hexlify(E.randomBytes(32));
    const id=h(),root=h(),doc=h(),provenance=h(),zero=E.ZeroHash;
    await (await c.registerCredential(id,root,doc,provenance,1,0,zero)).wait();
    let stored=await c.getCredential(id);assert.equal(stored[0],root);assert.equal(stored[1],doc);assert.equal(stored[7],1n);
    await assert.rejects(c.connect(other).registerCredential(h(),h(),h(),h(),1,0,zero));
    await assert.rejects(c.connect(other).revokeCredential(id));
    await assert.rejects(c.registerCredential(id,h(),doc,provenance,1,0,zero));
    await assert.rejects(c.registerCredential(h(),h(),h(),h(),1,2,zero));
    await assert.rejects(c.registerCredential(h(),h(),h(),h(),3,0,id));
    const next=h();await (await c.registerCredential(next,h(),h(),h(),2,1,id)).wait();
    stored=await c.getCredential(id);assert.equal(stored[7],3n);assert.equal(stored[8],next);
    await assert.rejects(c.registerCredential(h(),h(),h(),h(),2,0,id));
    await (await c.revokeCredential(next)).wait();assert.equal((await c.getCredential(next))[7],2n);
    await assert.rejects(c.revokeCredential.staticCall(next));
    // Test every odd/even path with the independent JavaScript implementation.
    for(const count of [1,2,3,4,5,17,128]){
      const leaves=Array.from({length:count},(_,index)=>({path:'fact.f'+index,label:'Fact '+index,type:'string',value:'private '+index,derivedFrom:'',salt:h(),index}));
      const levels=[leaves.map(proof.leafHash)];
      while(levels.at(-1).length>1){const row=levels.at(-1),next=[];for(let i=0;i<row.length;i+=2)next.push(proof.parent(row[i],row[Math.min(i+1,row.length-1)]));levels.push(next);}
      const root=levels.at(-1)[0];
      for(let i=0;i<count;i++){let index=i;const path=[];for(const row of levels.slice(0,-1)){path.push({sibling:row[Math.min(index^1,row.length-1)],side:index%2?'LEFT':'RIGHT'});index=Math.floor(index/2);}assert.equal(proof.verifyPath(leaves[i],path,count,root),true);assert.throws(()=>proof.verifyPath({...leaves[i],value:'changed'},path,count,root));}
    }
    console.log('PASS: registry authorization, immutable roots, unsupported assurance, atomic supersession, revocation and 7 independent Merkle tree shapes.');
  }finally{provider.destroy();await raw.disconnect();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
