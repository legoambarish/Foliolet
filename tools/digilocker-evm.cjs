// Isolated local demo chain. Never reads another worktree's keys or state.
const fs = require('node:fs'), path = require('node:path');
const ganache = require('ganache'), {Wallet} = require('ethers');
const root = path.resolve(__dirname, '..'), data = path.join(root, '.local-data');
const dir = path.join(data, 'evm'), keyFile = path.join(data, 'development-relay.key');
fs.mkdirSync(dir, {recursive: true});
if (!fs.existsSync(keyFile)) {
  if (fs.readdirSync(dir).length) throw Error('Retained demo chain has no signing key; restore it.');
  fs.writeFileSync(keyFile, Wallet.createRandom().privateKey, {flag:'wx', mode:0o600});
}
const key = fs.readFileSync(keyFile, 'utf8').trim();
const server = ganache.server({chain:{chainId:1337, networkId:1337, hardfork:'shanghai'},
  wallet:{accounts:[{secretKey:key, balance:'0x3635c9adc5dea00000'}]}, database:{dbPath:dir}, logging:{quiet:true}});
const port = Number(process.env.FOLIOLET_EVM_PORT || 8548);
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw Error('Invalid loopback EVM port');
server.listen(port, '127.0.0.1').then(() => console.log(`Isolated Foliolet demo EVM ready on loopback ${port}.`));
process.on('SIGINT', async () => {await server.close(); process.exit(0);});
process.on('SIGTERM', async () => {await server.close(); process.exit(0);});
