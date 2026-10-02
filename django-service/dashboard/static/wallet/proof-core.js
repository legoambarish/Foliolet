/* Protocol v1. Same binary encoding as the Java Merkle engine. No original file is needed. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else root.ProofTools = factory(root.ethers);
})(typeof globalThis !== 'undefined' ? globalThis : this, function (E) {
  'use strict';
  const FORMAT = 'salted-merkle-keccak-v1';
  const ABI = [
    'function operator() view returns(address)',
    'function getCredential(bytes32) view returns(bytes32,bytes32,bytes32,address,uint64,uint32,uint8,uint8,bytes32)'
  ];
  const fail = message => { throw Error(message); };
  function object(value,keys) {
    if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join(' ')!==keys.split(' ').sort().join(' '))fail('Malformed proof object');
  }
  function integer(value,min,max) {if(!Number.isSafeInteger(value)||value<min||value>max)fail('Invalid integer');}
  function text(value,limit,empty=false) {
    if(typeof value!=='string'||value.length>limit||(!empty&&!value.length)||/[\u0000-\u001f\u007f-\u009f]/.test(value))fail('Invalid text');
    // Java String.strip / Character.isWhitespace deliberately excludes NBSP, U+2007 and U+202F.
    const stripped=value.replace(/^[\u0020\u1680\u2000-\u2006\u2008-\u200a\u2028\u2029\u205f\u3000]+|[\u0020\u1680\u2000-\u2006\u2008-\u200a\u2028\u2029\u205f\u3000]+$/g,'');
    if(value!==stripped.normalize('NFC'))fail('Noncanonical text');
  }
  function path(value) {text(value,100);if(!/^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$/.test(value))fail('Invalid fact path');}
  function address(value) {if(typeof value!=='string'||!/^0x[0-9a-fA-F]{40}$/.test(value)||/^0x0{40}$/i.test(value)||!E.isAddress(value))fail('Invalid deployment address');}
  function canonicalLeaf(l) {
    object(l,'path label type value derivedFrom salt index');path(l.path);text(l.label,100);text(l.value,1000);
    if(l.type==='decimal') {
      if(!/^-?[0-9]{1,30}(\.[0-9]{1,12})?$/.test(l.value))fail('Invalid decimal');
      const negative=l.value.startsWith('-'),parts=l.value.replace(/^-/,'').split('.');
      const whole=parts[0].replace(/^0+(?=\d)/,''),fraction=(parts[1]||'').replace(/0+$/,'');
      const normalized=(negative&&(whole!=='0'||fraction)?'-':'')+whole+(fraction?'.'+fraction:'');
      if(l.value!==normalized)fail('Noncanonical decimal');
    } else if(l.type==='boolean') {if(!['true','false'].includes(l.value))fail('Noncanonical boolean');}
    else if(l.type==='date') {
      if(!/^\d{4}-\d{2}-\d{2}$/.test(l.value))fail('Invalid date');
      const date=new Date(l.value+'T00:00:00Z');
      if(!Number.isFinite(date.getTime())||date.toISOString().slice(0,10)!==l.value)fail('Invalid calendar date');
    } else if(l.type!=='string')fail('Unsupported fact type');
    if(typeof l.derivedFrom!=='string')fail('Invalid derivation');
    if(l.derivedFrom)path(l.derivedFrom);
    hex32(l.salt);integer(l.index,0,127);
  }
  function schema(b) {
    object(b,'format credentialId credentialVersion merkleRoot leafCount anchor provenance presentation claims envelopeHash platformSignature');
    if(b.format!==FORMAT)fail('Unsupported proof format');
    hex32(b.credentialId);hex32(b.merkleRoot);hex32(b.envelopeHash);
    integer(b.credentialVersion,1,2147483647);integer(b.leafCount,1,128);
    if(typeof b.platformSignature!=='string'||!/^0x[0-9a-fA-F]{130}$/.test(b.platformSignature))fail('Invalid signature shape');
    const a=b.anchor,p=b.presentation,v=b.provenance;
    object(a,'contract chainId operator txHash anchoredAt documentCommitment provenanceDigest provenanceCode');
    address(a.contract);address(a.operator);integer(a.chainId,1,Number.MAX_SAFE_INTEGER);integer(a.provenanceCode,0,1);
    if(a.txHash!==null)hex32(a.txHash);
    hex32(a.documentCommitment);hex32(a.provenanceDigest);seconds(a.anchoredAt);
    object(p,'grantId verifierLabel purpose nonce createdAt expiresAt oneTime');
    if(typeof p.grantId!=='string'||!/^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$/.test(p.grantId)||!/^[0-9a-f-]+$/.test(p.grantId))fail('Invalid grant ID');
    text(p.verifierLabel,150);text(p.purpose,250);hex32(p.nonce);seconds(p.createdAt);seconds(p.expiresAt);
    if(typeof p.oneTime!=='boolean')fail('Invalid one-time flag');
    object(v,'level explanation firstReceivedAt lastReceivedAt observations observedChanges enrollmentMatchesFirst agentId');
    text(v.explanation,4000);integer(v.observations,0,2147483647);
    for(const k of ['observedChanges','enrollmentMatchesFirst'])if(typeof v[k]!=='boolean')fail('Invalid provenance flag');
    for(const k of ['firstReceivedAt','lastReceivedAt'])if(v[k]!==null)seconds(v[k]);
    if(v.agentId!==null)text(v.agentId,100);
    if(!Array.isArray(b.claims)||!b.claims.length||b.claims.length>b.leafCount)fail('Invalid claims');
    for(const c of b.claims) {
      object(c,'leaf proof');canonicalLeaf(c.leaf);
      if(!Array.isArray(c.proof))fail('Invalid proof path');
      for(const step of c.proof){object(step,'sibling side');hex32(step.sibling);if(!['LEFT','RIGHT'].includes(step.side))fail('Invalid direction');}
    }
  }
  function trustPins(pins) {
    if(!pins||typeof pins!=='object')fail('Separately trusted registry, operator and chain ID are required');
    address(pins.contract);address(pins.operator);
    const value=pins.chainId;
    if(typeof value!=='number' && (typeof value!=='string'||! /^[1-9][0-9]*$/.test(value)))fail('Invalid trusted chain ID');
    const chainId=Number(value);integer(chainId,1,Number.MAX_SAFE_INTEGER);
    return {contract:pins.contract.toLowerCase(),operator:pins.operator.toLowerCase(),chainId};
  }
  function uint32(n) {
    if (!Number.isInteger(n) || n < 0 || n > 4294967295) fail('Invalid uint32');
    const b=new Uint8Array(4);new DataView(b.buffer).setUint32(0,n,false);return b;
  }
  function encode(...fields) {
    const parts=[];
    for(const s of fields) {if(typeof s!=='string')fail('Invalid string');const b=E.toUtf8Bytes(s);parts.push(uint32(b.length),b);}
    return E.concat(parts);
  }
  function hex32(h) {if(typeof h!=='string'||!/^0x[0-9a-fA-F]{64}$/.test(h))fail('Expected 32-byte hex');return E.getBytes(h);}
  function leafHash(l) {return E.keccak256(E.concat([new Uint8Array([0]),encode(FORMAT,l.path,l.label,l.type,l.value,l.derivedFrom),hex32(l.salt),uint32(l.index)]));}
  function parent(left,right) {return E.keccak256(E.concat([new Uint8Array([1]),hex32(left),hex32(right)]));}
  function verifyPath(leaf,proof,count,root) {
    if(!Number.isInteger(count)||count<1||count>128||leaf.index<0||leaf.index>=count||!Array.isArray(proof))fail('Invalid proof shape');
    let h=leafHash(leaf),index=leaf.index,width=count,depth=0;
    while(width>1) {
      const step=proof[depth++];if(!step)fail('Missing proof step');const right=index%2===0;
      if(step.side!==(right?'RIGHT':'LEFT'))fail('Wrong proof direction');
      if(right&&index+1>=width&&h!==step.sibling)fail('Invalid odd-node duplication');
      h=right?parent(h,step.sibling):parent(step.sibling,h);index=Math.floor(index/2);width=Math.ceil(width/2);
    }
    if(depth!==proof.length || h!==root)fail('Merkle root mismatch');return true;
  }
  function seconds(value) {
    if(typeof value!=='string'||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.0{1,9})?Z$/.test(value))fail('Invalid protocol timestamp');
    const ms=Date.parse(value);
    if(!Number.isFinite(ms)||new Date(ms).toISOString().slice(0,19)!==value.slice(0,19))fail('Invalid protocol timestamp');
    return String(ms/1000);
  }
  function provenanceHash(p) {return E.keccak256(encode('provenance-v1',p.level,p.explanation,
    p.firstReceivedAt?seconds(p.firstReceivedAt):'',p.lastReceivedAt?seconds(p.lastReceivedAt):'',String(p.observations),
    String(p.observedChanges),String(p.enrollmentMatchesFirst),p.agentId||''));}
  function envelopeHash(b) {
    const a=b.anchor,p=b.presentation;
    return E.keccak256(E.concat([new Uint8Array([3]),encode(b.format,b.credentialId,String(b.credentialVersion),b.merkleRoot,
      String(b.leafCount),a.contract.toLowerCase(),String(a.chainId),a.operator.toLowerCase(),a.documentCommitment,
      a.provenanceDigest,String(a.provenanceCode),seconds(a.anchoredAt),p.grantId,p.verifierLabel,p.purpose,p.nonce,
      seconds(p.createdAt),seconds(p.expiresAt),String(p.oneTime)),...b.claims.map(c=>hex32(leafHash(c.leaf)))]));
  }
  function verifyCryptography(b, now=Date.now()) {
    schema(b);
    if(b.format!==FORMAT||!Array.isArray(b.claims)||!b.claims.length||b.claims.length>128)fail('Unsupported proof format');
    const indices=new Set(),paths=new Set();
    for(const c of b.claims) {
      if(indices.has(c.leaf.index)||paths.has(c.leaf.path))fail('Duplicate fact');
      indices.add(c.leaf.index);paths.add(c.leaf.path);verifyPath(c.leaf,c.proof,b.leafCount,b.merkleRoot);
    }
    if(provenanceHash(b.provenance)!==b.anchor.provenanceDigest)fail('Source assurance metadata was changed');
    if(!['SELF_ENROLLED','FIRST_SEEN_TRACKED'].includes(b.provenance.level) || b.anchor.provenanceCode!==(b.provenance.level==='FIRST_SEEN_TRACKED'?1:0)) fail('Unsupported assurance');
    const h=envelopeHash(b);if(h!==b.envelopeHash)fail('Presentation context was changed');
    if(E.verifyMessage(hex32(h),b.platformSignature).toLowerCase()!==b.anchor.operator.toLowerCase())fail('Platform signature invalid');
    const p=b.presentation,start=Date.parse(p.createdAt),end=Date.parse(p.expiresAt);
    if(end<=now||start>now+30000||end<=start||end>start+604800000)fail('Presentation expired or invalid');
    return {proofValid:true,signatureValid:true};
  }
  async function verifyChain(b,provider,pins) {
    const {contract:expectedContract,chainId:expectedChain,operator:expectedOperator}=trustPins(pins);
    verifyCryptography(b);
    // The caller must provision these outside the service/bundle being checked.
    if(b.anchor.contract.toLowerCase()!==expectedContract)fail('Unexpected registry');
    if(b.anchor.chainId!==expectedChain)fail('Unexpected chain');
    if(b.anchor.operator.toLowerCase()!==expectedOperator)fail('Unexpected operator');
    const network=await provider.getNetwork();if(network.chainId!==BigInt(b.anchor.chainId))fail('RPC is on a different chain');
    const contract=new E.Contract(b.anchor.contract,ABI,provider);
    const [operator,c]=await Promise.all([contract.operator(),contract.getCredential(b.credentialId)]);
    if(operator.toLowerCase()!==b.anchor.operator.toLowerCase()||c[3].toLowerCase()!==operator.toLowerCase())fail('Wrong registry operator');
    if(c[0]!==b.merkleRoot||c[1]!==b.anchor.documentCommitment||c[2]!==b.anchor.provenanceDigest||c[4]!==BigInt(seconds(b.anchor.anchoredAt))||c[5]!==BigInt(b.credentialVersion)||c[6]!==BigInt(b.anchor.provenanceCode))fail('On-chain commitment mismatch');
    if(c[7]!==1n)fail(c[7]===2n?'Credential revoked':c[7]===3n?'Credential superseded':'Credential missing');
    // Signature verification is repeated after slow RPC calls so expiry cannot pass mid-check.
    verifyCryptography(b);
    return {proofValid:true,signatureValid:true,anchorMatches:true,current:true};
  }
  return {FORMAT,ABI,uint32,encode,leafHash,parent,verifyPath,provenanceHash,envelopeHash,verifyCryptography,verifyChain,trustPins};
});
