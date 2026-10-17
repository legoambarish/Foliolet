package com.sih26190.dms.foli;

import java.util.*;
import org.apache.pdfbox.Loader;
import org.bouncycastle.cms.*;
import org.bouncycastle.cert.X509CertificateHolder;
import org.bouncycastle.cms.jcajce.JcaSimpleSignerInfoVerifierBuilder;

/** Offline mathematics only, executed within the bounded reader subprocess. */
final class PdfSignatureIntegrity {
  static String inspect(byte[] bytes) {
    try(var document=Loader.loadPDF(bytes)) {
      var signatures=document.getSignatureDictionaries();
      if(signatures.isEmpty())return "NOT_APPLICABLE";
      if(signatures.size()>8)return "INCONCLUSIVE";
      boolean current=false,unsupported=false;
      for(var signature:signatures) {
        FoliExtractionService.checkCancel();
        if(!Set.of("adbe.pkcs7.detached","ETSI.CAdES.detached").contains(Objects.toString(signature.getSubFilter(),""))){unsupported=true;continue;}
        var range=signature.getByteRange();
        if(range==null || range.length!=4 || range[0]!=0 || range[1]<=0 || range[2]<=range[1] || range[3]<0
            || (long)range[2]+range[3]>bytes.length)return "FAILED";
        // Only the PDF hexadecimal Contents token may be excluded from coverage.
        if(bytes[range[1]]!='<' || bytes[range[2]-1]!='>')return "INCONCLUSIVE";
        for(int i=range[1]+1;i<range[2]-1;i++)if(Character.digit((char)bytes[i],16)<0)return "INCONCLUSIVE";
        byte[] contents=signature.getContents(bytes);
        var buffer=new java.io.ByteArrayInputStream(contents);
        var asn1=new org.bouncycastle.asn1.ASN1InputStream(buffer);
        var content=org.bouncycastle.asn1.cms.ContentInfo.getInstance(asn1.readObject());
        // PDF reserves a fixed-size Contents slot; only zero padding may follow CMS.
        while(buffer.available()>0)if(buffer.read()!=0)return "INCONCLUSIVE";
        var cms=new CMSSignedData(new CMSProcessableByteArray(signature.getSignedContent(bytes)),content);
        var signers=cms.getSignerInfos().getSigners();if(signers.size()!=1)return "INCONCLUSIVE";
        for(var signer:signers) {
          var certificates=cms.getCertificates().getMatches(signer.getSID());
          if(certificates.size()!=1)return "INCONCLUSIVE";
          if(!signer.verify(new JcaSimpleSignerInfoVerifierBuilder().build((X509CertificateHolder)certificates.iterator().next())))return "FAILED";
        }
        current|=(long)range[2]+range[3]==bytes.length;
      }
      return current && !unsupported?"PASSED":"INCONCLUSIVE";
    }catch(CMSException e){return "FAILED";}
    catch(Exception e){return "INCONCLUSIVE";}
  }
}
