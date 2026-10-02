const fs = require('node:fs');
const path = require('node:path');
const solc = require('solc');
if (!solc.version().startsWith('0.8.19')) throw Error('Install the pinned Solidity 0.8.19 compiler');
const name = 'SelectiveDisclosureRegistry';
const source = fs.readFileSync(path.join(__dirname, '../contracts', name + '.sol'), 'utf8');
const output = JSON.parse(solc.compile(JSON.stringify({language:'Solidity', sources:{[name+'.sol']:{content:source}},
  settings:{optimizer:{enabled:true,runs:200},evmVersion:'paris',outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}}})));
for(const e of output.errors || []) { if(e.severity === 'error') throw Error(e.formattedMessage); }
const contract = output.contracts[name+'.sol'][name];
const dir = path.join(__dirname, '../src/main/resources/solidity', name);
fs.mkdirSync(dir,{recursive:true});
fs.writeFileSync(path.join(dir,name+'.abi'), JSON.stringify(contract.abi,null,2)+'\n');
fs.writeFileSync(path.join(dir,name+'.bin'),contract.evm.bytecode.object+'\n');
console.log('Compiled '+name+' using '+solc.version());
