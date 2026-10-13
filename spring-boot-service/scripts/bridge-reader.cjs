const fs=require('node:fs');const B=require('../../django-service/dashboard/static/wallet/bridge-core.js');
async function main(){const [file,pinFile,...args]=process.argv.slice(2);if(!file||!pinFile)throw Error('Usage: node bridge-reader.cjs bundle.json independently-provisioned-pins.json [--historical decision.json]');
 const bundle=JSON.parse(fs.readFileSync(file));const pins=JSON.parse(fs.readFileSync(pinFile));let options={};if(args[0]==='--historical'){const decision=JSON.parse(fs.readFileSync(args[1]));options=B.receiptOptions(decision,bundle,pins);}
 const result=await B.verify(bundle,pins,options);console.log(JSON.stringify(result,null,2));process.exitCode=result.result==='PASS'?0:result.result==='FAIL'?1:2;
}main().catch(e=>{console.error(e.message);process.exitCode=2;});
