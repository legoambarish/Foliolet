const ganache = require('ganache');
const path = require('node:path');
const fs = require('node:fs');
const { Wallet } = require('ethers');
const dir = path.resolve(__dirname, '../../.local-data/evm');
const keyPath = path.resolve(__dirname, '../../.local-data/development-relay.key');
fs.mkdirSync(dir,{recursive:true});
// Keep the loopback development identity stable without publishing signing material.
if (!fs.existsSync(keyPath)) {
  if (fs.readdirSync(dir).length) throw Error('Existing EVM data has no relay key. Restore development-relay.key; do not reset the identity.');
  fs.writeFileSync(keyPath, Wallet.createRandom().privateKey+'\n', {flag:'wx',mode:0o600});
}
const key = fs.readFileSync(keyPath,'utf8').trim();
const operator = new Wallet(key).address;
const server = ganache.server({
  chain:{chainId:1337,networkId:1337,hardfork:'shanghai'},
  wallet:{accounts:[{secretKey:key,balance:'0x3635c9adc5dea00000'}]},
  database:{dbPath:dir},logging:{quiet:true}
});
server.listen(8545,'127.0.0.1').then(()=>console.log('Persistent development EVM: http://127.0.0.1:8545 (chain 1337), operator '+operator));
async function stop(){await server.close();process.exit(0);}
process.on('SIGINT',stop);process.on('SIGTERM',stop);
