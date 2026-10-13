const ganache = require('ganache'); const fs = require('node:fs'); const path = require('node:path');
const directory = process.env.BRIDGE_CHAIN_DIR || path.resolve(__dirname, '../../.bridge-data/chain');
fs.mkdirSync(directory, {recursive:true});
const server = ganache.server({wallet:{mnemonic:'test test test test test test test test test test test junk',totalAccounts:10,defaultBalance:1000},chain:{chainId:1337},miner:{blockTime:3},database:{dbPath:directory},server:{ws:false},logging:{quiet:true}});
server.listen(Number(process.env.PORT || 8545), process.env.HOST || '127.0.0.1').then(()=>console.log('Public test mnemonic chain ready; never fund these accounts with real assets'));
for(const signal of ['SIGTERM','SIGINT']) process.on(signal,async()=>{await server.close();process.exit(0);});
