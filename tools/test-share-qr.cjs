// Exercise the real share receipt JS: copied and QR-encoded URL must match.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
test('copy and QR encode the exact public receipt value', async()=>{
  const url='https://receipt-test.trycloudflare.com/verify/'+'a'.repeat(64)+'/';
  let onload, click, copied, encoded;
  const nodes={
    'share-url':{value:url}, 'copy-status':{},
    'copy-link':{addEventListener:(event,fn)=>{click=fn;}}, 'qr-code':{},
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../django-service/dashboard/static/wallet/wallet.js'),'utf8'),{
    document:{addEventListener:(event,fn)=>{onload=fn;},getElementById:id=>nodes[id]},
    navigator:{clipboard:{writeText:async value=>{copied=value;}}},
    qrcode:()=>({addData:value=>{encoded=value;},make:()=>{},createImgTag:()=>'<img>'}),
  });
  onload(); await click();
  assert.equal(encoded,url); assert.equal(copied,url); assert.equal(encoded,copied);
});
