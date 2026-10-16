/* Operator provisioning from this isolated launcher's local deployment record.
 * No trust is taken from a disclosure bundle or Spring discovery endpoint. */
const fs = require('node:fs');
const path = require('node:path');
const {Wallet, JsonRpcProvider, Contract} = require('ethers');
const root = path.resolve(__dirname, '..');
async function main() {
  const state = process.env.FOLIOLET_DATA_DIR || path.join(root, '.local-data');
  const operator = new Wallet(fs.readFileSync(path.join(state, 'development-relay.key'), 'utf8').trim()).address;
  const address = fs.readFileSync(path.join(state, 'chain', `SelectiveDisclosureRegistry-1337-${operator.toLowerCase()}.address`), 'utf8').trim();
  const provider = new JsonRpcProvider('http://127.0.0.1:8548', undefined, {batchMaxCount:1});
  try {
    if ((await provider.getNetwork()).chainId !== 1337n || (await provider.getCode(address)) === '0x') throw Error('Isolated registry deployment is unavailable');
    const registry = new Contract(address, ['function operator() view returns (address)'], provider);
    if ((await registry.operator()).toLowerCase() !== operator.toLowerCase()) throw Error('Isolated registry operator mismatch');
    const pins = {contract:address, operator, chainId:1337};
    const file = path.join(state, 'trusted-deployment.json');
    if (fs.existsSync(file)) {
      const old = JSON.parse(fs.readFileSync(file, 'utf8'));
      if (Object.keys(pins).some(key => String(old[key]).toLowerCase() !== String(pins[key]).toLowerCase())) throw Error('Retained trust pins differ; no file overwritten');
    } else fs.writeFileSync(file, JSON.stringify(pins, null, 2), {flag:'wx'});
    console.log('Isolated operator trust pins checked against the local registry deployment.');
  } finally {provider.destroy();}
}
main().catch(error => {console.error(error.message);process.exitCode=1;});
