package com.sih26190.dms.bridge;

import java.io.*;
import java.security.cert.X509Certificate;
import java.util.*;
import javax.xml.XMLConstants;
import javax.xml.crypto.dsig.XMLSignatureFactory;
import javax.xml.crypto.dsig.dom.DOMValidateContext;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.*;

/** Narrow whole-document XMLDSIG profile. Embedded KeyInfo never establishes trust. */
public final class XmlSourceValidator {
  private XmlSourceValidator() {}

  public static Map<String, Object> inspect(
      byte[] bytes, X509Certificate pin, String allowedIssuer, String allowedType)
      throws Exception {
    if (bytes.length == 0 || bytes.length > 131072)
      throw new IllegalArgumentException("XML must be 1-128 KiB");
    var factory = DocumentBuilderFactory.newInstance();
    factory.setNamespaceAware(true);
    factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
    factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
    factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
    factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
    factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
    factory.setXIncludeAware(false);
    factory.setExpandEntityReferences(false);
    var builder = factory.newDocumentBuilder();
    builder.setErrorHandler(
        new org.xml.sax.helpers.DefaultHandler() {
          @Override
          public void fatalError(org.xml.sax.SAXParseException e) throws org.xml.sax.SAXException {
            throw e;
          }
        });
    var document = builder.parse(new ByteArrayInputStream(bytes));
    var root = document.getDocumentElement();
    var signatures =
        document.getElementsByTagNameNS(javax.xml.crypto.dsig.XMLSignature.XMLNS, "Signature");
    boolean supported =
        root.getTagName().equals("IssuedDocument") && root.getNamespaceURI() == null;
    String classification = signatures.getLength() == 0 ? "SELF_ASSERTED" : "UNKNOWN";
    String signatureStatus =
        signatures.getLength() == 0 ? "UNSIGNED" : "SIGNATURE_PRESENT_UNTRUSTED";
    boolean valid = false;
    if (signatures.getLength() == 1 && supported && pin != null) {
      pin.checkValidity();
      if (!root.getAttribute("issuer").equals(allowedIssuer)
          || !root.getAttribute("type").equals(allowedType))
        throw new IllegalArgumentException(
            "Issuer or document type is outside configured certificate scope");
      var context = new DOMValidateContext(pin.getPublicKey(), signatures.item(0));
      context.setProperty("org.jcp.xml.dsig.secureValidation", Boolean.TRUE);
      context.setURIDereferencer(
          (reference, ctx) -> {
            if (!"".equals(reference.getURI()))
              throw new javax.xml.crypto.URIReferenceException(
                  "Only whole-document references are supported");
            return XMLSignatureFactory.getInstance("DOM")
                .getURIDereferencer()
                .dereference(reference, ctx);
          });
      var signature = XMLSignatureFactory.getInstance("DOM").unmarshalXMLSignature(context);
      var references = signature.getSignedInfo().getReferences();
      if (references.size() != 1
          || !"".equals(references.get(0).getURI())
          || !references
              .get(0)
              .getDigestMethod()
              .getAlgorithm()
              .equals("http://www.w3.org/2001/04/xmlenc#sha256"))
        throw new IllegalArgumentException("Unsupported signature reference profile");
      String algorithm = signature.getSignedInfo().getSignatureMethod().getAlgorithm();
      if (!Set.of(
              "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
              "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256")
          .contains(algorithm))
        throw new IllegalArgumentException("Unsupported signature algorithm");
      for (var transform : references.get(0).getTransforms())
        if (!Set.of(
                "http://www.w3.org/2000/09/xmldsig#enveloped-signature",
                "http://www.w3.org/2001/10/xml-exc-c14n#")
            .contains(transform.getAlgorithm()))
          throw new IllegalArgumentException("Unsupported signature transform");
      valid = signature.validate(context);
      signatureStatus = valid ? "VALID_UNDER_EXPLICIT_CERTIFICATE_PIN" : "INVALID_SIGNATURE";
      classification = valid ? "SIGNED_SOURCE" : "UNKNOWN";
    }
    if (signatures.getLength() > 1) {
      classification = "UNKNOWN";
      signatureStatus = "MULTIPLE_SIGNATURES_UNSUPPORTED";
    }
    var fields = new ArrayList<Map<String, Object>>();
    if (supported) {
      for (Node node = root.getFirstChild(); node != null; node = node.getNextSibling())
        if (node instanceof Element e && e.getTagName().equals("Facts")) {
          for (Node child = e.getFirstChild(); child != null; child = child.getNextSibling())
            if (child instanceof Element fact && fact.getTagName().equals("Fact")) {
              String path = fact.getAttribute("path"), value = fact.getTextContent();
              if (!path.matches("[a-zA-Z0-9_.]{1,80}")
                  || value.length() > 240
                  || fields.size() >= 32)
                throw new IllegalArgumentException("Imported field exceeds bound");
              fields.add(Map.of("path", path, "value", value, "confirmed", false));
            }
        }
    }
    return Map.of(
        "classification",
        classification,
        "signatureStatus",
        signatureStatus,
        "supportedProfile",
        supported ? "foliolet-issued-xml-v1" : "UNSUPPORTED_XML_SCHEMA",
        "fields",
        fields,
        "sha256",
        java.util.HexFormat.of()
            .formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(bytes)),
        "rawBytesRetained",
        false,
        "authorityNote",
        "A transport/provider name does not establish institutional authority. Imported fields"
            + " require review and cannot issue credentials.");
  }
}
