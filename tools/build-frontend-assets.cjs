const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname,'..');
const dir = path.join(root,'django-service/dashboard/static/wallet/vendor');
fs.mkdirSync(dir,{recursive:true});
fs.copyFileSync(path.join(root,'spring-boot-service/node_modules/ethers/dist/ethers.umd.min.js'),path.join(dir,'ethers.umd.min.js'));
fs.copyFileSync(path.join(root,'spring-boot-service/node_modules/ethers/LICENSE.md'),path.join(dir,'ethers-LICENSE.md'));
fs.copyFileSync(path.join(root,'node_modules/qrcode-generator/qrcode.js'),path.join(dir,'qrcode.js'));
console.log('Bundled local proof-verification and QR assets. No CDN is required.');
