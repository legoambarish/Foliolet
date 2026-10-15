"""Live read-only Foli gate, creating only new synthetic holder/doc fixtures."""
import hashlib
import json
from pathlib import Path
import secrets
import time
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/".local-data/foli"
API="http://127.0.0.1:8080"
events=[]


def check(ok,name):
    assert ok,name
    events.append({"test":name,"result":"PASS"})
    print(time.strftime("%H:%M:%S"),"PASS",name,flush=True)


def call(method,path,auth=None,**kwargs):
    return requests.request(method,API+path,auth=tuple(auth) if auth else None,timeout=(3,200),**kwargs)


def main():
    auths=[]
    for i in range(2):
        auth=["foli-reading-"+secrets.token_hex(5),secrets.token_urlsafe(20)]
        check(call("POST","/api/auth/register",json={"username":auth[0],"password":auth[1],"role":"HOLDER"}).status_code==200,"Synthetic holder registration "+str(i+1))
        auths.append(auth)
    docs={}
    for name in ["long-contract-125-pages.pdf","plain.txt","table.csv","corrupt.pdf","protected.pdf","unsupported.docx","unreadable.pdf"]:
        path=OUT/"fixtures"/name
        response=call("POST","/api/wallet/documents",auths[0],files={"file":(name,path.read_bytes())},data={"displayName":name,"category":"Other"})
        check(response.status_code==200,"Synthetic enrollment "+name)
        docs[name]="wallet:"+response.json()["id"]
    response=call("POST","/api/wallet/documents",auths[1],files={"file":("other-private.txt",b"OTHER HOLDER SECRET 4A981")},data={"displayName":"other-private","category":"Other"})
    other="wallet:"+response.json()["id"]
    check(call("GET","/api/foli/documents").status_code==401,"Anonymous list denied")
    listing=call("GET","/api/foli/documents",auths[0])
    check(listing.status_code==200 and other not in {d["id"] for d in listing.json()},"Picker is owner-scoped")
    check("filePath" not in listing.text and "password" not in listing.text,"Picker omits private paths and credentials")
    doc=docs["long-contract-125-pages.pdf"]
    manifest=call("GET","/api/foli/manifest",auths[0],params={"documentId":doc}).json()
    check(manifest.get("totalPages")==125 and manifest.get("accountedPages")==125,"All 125 pages accounted for")
    check(manifest.get("readablePages")==125,"All digital pages readable")
    source=call("GET","/api/foli/source",auths[0],params={"documentId":doc,"hash":manifest["sourceHash"],"page":125})
    check(source.status_code==200 and "Notwithstanding every earlier renewal" in source.json()["page"]["text"],"Late-page exception is accessible")
    for name,path,params in [
        ("Cross-user manifest","manifest",{"documentId":doc}),
        ("Cross-user source","source",{"documentId":doc,"hash":manifest["sourceHash"],"page":125}),
        ("Cross-user image","page",{"documentId":doc,"hash":manifest["sourceHash"],"page":125}),
    ]: check(call("GET","/api/foli/"+path,auths[1],params=params).status_code==404,name+" denied")
    check(call("GET","/api/foli/source",auths[0],params={"documentId":doc,"hash":"0"*64,"page":125}).status_code==409,"Stale citation hash denied")
    check(call("GET","/api/foli/source",auths[0],params={"documentId":doc,"hash":manifest["sourceHash"],"page":126}).status_code==404,"Out-of-range page denied")
    for filename,status in [("corrupt.pdf",422),("protected.pdf",422),("unsupported.docx",415)]:
        check(call("GET","/api/foli/manifest",auths[0],params={"documentId":docs[filename]}).status_code==status,"Clear failure "+filename)
    unreadable=call("GET","/api/foli/manifest",auths[0],params={"documentId":docs["unreadable.pdf"]}).json()
    check(not unreadable.get("complete",True) and unreadable["pages"][0]["status"]=="UNREADABLE","Unreadable scan remains uncertain")
    check(call("GET","/api/foli/manifest",auths[0],params={"documentId":"legacy:../vault.key"}).status_code==404,"Typed-ID traversal rejected")
    original=call("GET","/api/wallet/documents/"+doc[7:]+"/file",auths[0]).content
    check(hashlib.sha256(original).hexdigest()==hashlib.sha256((OUT/"fixtures/long-contract-125-pages.pdf").read_bytes()).hexdigest(),"Original bytes preserved")
    (OUT/"reading-fixture.json").write_text(json.dumps({"auth":auths,"documents":docs,"other":other},indent=2),encoding="utf-8")
    (OUT/"phase-1-live.json").write_text(json.dumps({"checks":events,"failures":0},indent=2),encoding="utf-8")
    print("Live reading gate:",len(events),"passed",flush=True)


if __name__=="__main__": main()
