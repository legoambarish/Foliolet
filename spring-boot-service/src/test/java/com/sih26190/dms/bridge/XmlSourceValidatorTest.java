package com.sih26190.dms.bridge;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.cert.X509Certificate;
import java.util.*;
import javax.xml.crypto.dsig.*;
import javax.xml.crypto.dsig.dom.DOMSignContext;
import javax.xml.crypto.dsig.spec.*;
import javax.xml.parsers.*;
import javax.xml.transform.*;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import org.junit.jupiter.api.Test;

class XmlSourceValidatorTest {
  private final byte[] unsigned =
      "<IssuedDocument issuer=\"TEST University\" type=\"transcript\"><Facts><Fact path=\"education.cgpa\">8.7</Fact></Facts></IssuedDocument>"
          .getBytes(StandardCharsets.UTF_8);

  private KeyPair keys() throws Exception {
    var generator = KeyPairGenerator.getInstance("RSA");
    generator.initialize(2048);
    return generator.generateKeyPair();
  }

  private X509Certificate pin(KeyPair keys) {
    var pin = mock(X509Certificate.class);
    when(pin.getPublicKey()).thenReturn(keys.getPublic());
    return pin;
  }

  private byte[] sign(KeyPair keys) throws Exception {
    var parser = DocumentBuilderFactory.newInstance();
    parser.setNamespaceAware(true);
    var document = parser.newDocumentBuilder().parse(new ByteArrayInputStream(unsigned));
    var factory = XMLSignatureFactory.getInstance("DOM");
    var reference =
        factory.newReference(
            "",
            factory.newDigestMethod(DigestMethod.SHA256, null),
            List.of(
                factory.newTransform(Transform.ENVELOPED, (TransformParameterSpec) null),
                factory.newTransform(
                    CanonicalizationMethod.EXCLUSIVE, (TransformParameterSpec) null)),
            null,
            null);
    var info =
        factory.newSignedInfo(
            factory.newCanonicalizationMethod(
                CanonicalizationMethod.EXCLUSIVE, (C14NMethodParameterSpec) null),
            factory.newSignatureMethod(SignatureMethod.RSA_SHA256, null),
            List.of(reference));
    factory
        .newXMLSignature(info, null)
        .sign(new DOMSignContext(keys.getPrivate(), document.getDocumentElement()));
    var output = new ByteArrayOutputStream();
    TransformerFactory.newInstance()
        .newTransformer()
        .transform(new DOMSource(document), new StreamResult(output));
    return output.toByteArray();
  }

  @Test
  void unsignedCannotEarnSourceAuthority() throws Exception {
    var result = XmlSourceValidator.inspect(unsigned, null, "", "");
    assertEquals("SELF_ASSERTED", result.get("classification"));
    assertEquals(false, result.get("rawBytesRetained"));
    assertEquals(false, ((Map<?, ?>) ((List<?>) result.get("fields")).get(0)).get("confirmed"));
  }

  @Test
  void untrustedSignatureAndFilenameCannotGrantAuthority() throws Exception {
    var result = XmlSourceValidator.inspect(sign(keys()), null, "", "");
    assertEquals("UNKNOWN", result.get("classification"));
    assertEquals("SIGNATURE_PRESENT_UNTRUSTED", result.get("signatureStatus"));
  }

  @Test
  void realCryptographicSignatureRequiresScopedExternalPin() throws Exception {
    var keys = keys();
    var result = XmlSourceValidator.inspect(sign(keys), pin(keys), "TEST University", "transcript");
    assertEquals("SIGNED_SOURCE", result.get("classification"));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            XmlSourceValidator.inspect(
                sign(keys), pin(keys), "Different University", "transcript"));
  }

  @Test
  void changedBytesAndWrongKeyFailClosed() throws Exception {
    var keys = keys();
    byte[] tampered =
        new String(sign(keys), StandardCharsets.UTF_8)
            .replace("8.7", "9.9")
            .getBytes(StandardCharsets.UTF_8);
    assertEquals(
        "UNKNOWN",
        XmlSourceValidator.inspect(tampered, pin(keys), "TEST University", "transcript")
            .get("classification"));
    assertEquals(
        "UNKNOWN",
        XmlSourceValidator.inspect(sign(keys), pin(keys()), "TEST University", "transcript")
            .get("classification"));
  }

  @Test
  void externalEntitiesAndUnsupportedSchemasDoNotProduceTrustedFacts() throws Exception {
    assertThrows(
        Exception.class,
        () ->
            XmlSourceValidator.inspect(
                "<!DOCTYPE x [<!ENTITY e SYSTEM 'file:///private'>]><x>&e;</x>".getBytes(),
                null,
                "",
                ""));
    assertEquals(
        "UNSUPPORTED_XML_SCHEMA",
        XmlSourceValidator.inspect(
                "<DigiLockerVerified>yes</DigiLockerVerified>".getBytes(), null, "", "")
            .get("supportedProfile"));
  }
}
