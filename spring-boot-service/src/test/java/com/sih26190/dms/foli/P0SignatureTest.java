package com.sih26190.dms.foli;

import java.io.*;
import java.math.BigInteger;
import java.security.*;
import java.util.*;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.*;
import org.apache.pdfbox.pdmodel.interactive.digitalsignature.PDSignature;
import org.bouncycastle.asn1.x500.X500Name;
import org.bouncycastle.cert.jcajce.JcaX509v3CertificateBuilder;
import org.bouncycastle.cms.*;
import org.bouncycastle.cms.jcajce.JcaSignerInfoGeneratorBuilder;
import org.bouncycastle.operator.jcajce.*;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class P0SignatureTest {
  @Test void unsignedSelfSignedAndTamperedRemainSeparateFromIssuerTrust() throws Exception {
    var plain=new ByteArrayOutputStream();
    try(var pdf=new PDDocument()){pdf.addPage(new PDPage());pdf.save(plain);}
    assertEquals("NOT_APPLICABLE",PdfSignatureIntegrity.inspect(plain.toByteArray()));
    var generator=KeyPairGenerator.getInstance("RSA");generator.initialize(2048);var pair=generator.generateKeyPair();
    var name=new X500Name("CN=Fictional untrusted test signer");
    var contentSigner=new JcaContentSignerBuilder("SHA256withRSA").build(pair.getPrivate());
    var cert=new JcaX509v3CertificateBuilder(name,BigInteger.ONE,new Date(0),new Date(System.currentTimeMillis()+86400000),name,pair.getPublic()).build(contentSigner);
    var signed=new ByteArrayOutputStream();
    try(var pdf=Loader.loadPDF(plain.toByteArray())) {
      var signature=new PDSignature();signature.setFilter(PDSignature.FILTER_ADOBE_PPKLITE);signature.setSubFilter(PDSignature.SUBFILTER_ADBE_PKCS7_DETACHED);
      signature.setName("Fictional signature");
      pdf.addSignature(signature,stream->{
        try {
          var cms=new CMSSignedDataGenerator();cms.addCertificate(cert);
          cms.addSignerInfoGenerator(new JcaSignerInfoGeneratorBuilder(new JcaDigestCalculatorProviderBuilder().build()).build(new JcaContentSignerBuilder("SHA256withRSA").build(pair.getPrivate()),cert));
          return cms.generate(new CMSProcessableByteArray(stream.readAllBytes()),false).getEncoded();
        }catch(Exception e){throw new IOException(e);}
      });pdf.saveIncremental(signed);
    }
    byte[] bytes=signed.toByteArray();assertEquals("PASSED",PdfSignatureIntegrity.inspect(bytes));
    String text=new String(bytes,java.nio.charset.StandardCharsets.ISO_8859_1);int at=text.indexOf("Fictional signature");assertTrue(at>=0);
    bytes[at]='X';assertEquals("FAILED",PdfSignatureIntegrity.inspect(bytes));
  }
}
