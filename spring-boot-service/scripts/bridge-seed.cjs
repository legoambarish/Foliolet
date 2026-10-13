const fs = require('node:fs'); const path = require('node:path'); const E = require('ethers');
const rpc = process.env.BLOCKCHAIN_RPC_URL || 'http://127.0.0.1:8545';
const dir = process.env.BRIDGE_CONFIG_DIR || path.resolve(__dirname,'../../.bridge-data/config');
const account = i => E.HDNodeWallet.fromPhrase('test test test test test test test test test test test junk',undefined,`m/44'/60'/0'/0/${i}`);
async function main(){
 const provider = new E.JsonRpcProvider(rpc); const signer = new E.NonceManager(account(0).connect(provider));
 if(Number((await provider.getNetwork()).chainId)!==1337)throw Error('Only the local 1337 test chain can be seeded');
 fs.mkdirSync(dir,{recursive:true}); const file=path.join(dir,'bridge-pins.json');
 if(fs.existsSync(file)){const old=JSON.parse(fs.readFileSync(file));const code=await provider.getCode(old.registry);if(code==='0x'||E.keccak256(code)!==old.codeHash||old.chainId!==1337||!fs.existsSync(path.join(dir,'demo.env'))||!fs.existsSync(path.join(dir,'trusted-deployment.json')))throw Error('Persisted deployment/config differs. Reset demo volumes together, never silently replace pins.');const contract=new E.Contract(old.registry,['function governance() view returns(address)'],provider);if((await contract.governance()).toLowerCase()!==old.governance.toLowerCase())throw Error('Stored governance pin differs');console.log('Retaining existing deployment and pins');return;}
 const base=path.join(__dirname,'../src/main/resources/solidity');
 const load=name=>({abi:JSON.parse(fs.readFileSync(path.join(base,name,name+'.abi'))),bytecode:'0x'+fs.readFileSync(path.join(base,name,name+'.bin'),'utf8').trim()});
 const deploy=async(name,args=[])=>{const c=load(name);const deployed=await new E.ContractFactory(c.abi,c.bytecode,signer).deploy(...args);await deployed.waitForDeployment();return deployed;};
 const bridge=await deploy('EvidenceBridgeRegistry',[account(0).address]); const selective=await deploy('SelectiveDisclosureRegistry'); const legacy=await deploy('DocumentRegistry');
 for(const [i,label,type] of [[1,'Test University','internship-eligibility/v1'],[2,'Test Employer','income-evidence/v1']]) await(await bridge.recognize(account(i).address,label,E.id(type))).wait();
 const pins={format:'foliolet-trust-pins-v1',chainId:1337,registry:await bridge.getAddress(),governance:account(0).address,codeHash:E.keccak256(await provider.getCode(await bridge.getAddress())),rpc:'http://127.0.0.1:8545',demo:true,actors:['Test Governance','Test University','Test Employer','Rogue Converter','Test Holder A','Test Holder B','Test Internship Verifier','Test Tenant Verifier'].map((name,i)=>({name,address:account(i).address})),claimTypes:['internship-eligibility/v1','income-evidence/v1']};
 fs.writeFileSync(file,JSON.stringify(pins,null,2)+'\n');
 fs.writeFileSync(path.join(dir,'trusted-deployment.json'),JSON.stringify({contractAddress:await selective.getAddress(),operator:account(0).address,chainId:1337},null,2));
 let env=`BLOCKCHAIN_PRIVATE_KEY=${account(0).privateKey}\nBLOCKCHAIN_CONTRACT_ADDRESS=${await legacy.getAddress()}\nSELECTIVE_CONTRACT_ADDRESS=${await selective.getAddress()}\nBRIDGE_REGISTRY=${pins.registry}\nBRIDGE_GOVERNANCE=${pins.governance}\n`;
 for(const [name,i] of [['GOVERNANCE',0],['UNIVERSITY',1],['EMPLOYER',2],['ROGUE',3],['INTERNSHIP_VERIFIER',6],['TENANT_VERIFIER',7]]) env+=`BRIDGE_${name}_KEY=${account(i).privateKey}\n`;
 fs.writeFileSync(path.join(dir,'demo.env'),env,{mode:0o600}); console.log('Seeded test registry, scoped issuers and separately provisioned pins. Public test keys only.');
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
