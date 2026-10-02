package com.sih26190.dms.selective;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.stereotype.Component;

@Component
public class WalletJson {
  private final ObjectMapper mapper =
      new ObjectMapper()
          .registerModule(new JavaTimeModule())
          .disable(com.fasterxml.jackson.databind.SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
  private final ObjectMapper proofMapper = mapper.copy()
      .enable(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
      .enable(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_MISSING_CREATOR_PROPERTIES)
      .enable(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES)
      .enable(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
      .enable(com.fasterxml.jackson.core.JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
      .disable(com.fasterxml.jackson.databind.DeserializationFeature.ACCEPT_FLOAT_AS_INT)
      .disable(com.fasterxml.jackson.databind.MapperFeature.ALLOW_COERCION_OF_SCALARS);

  public WalletJson() {
    // Jackson's global scalar switch does not prevent boolean/number-to-String coercion.
    var textual = proofMapper.coercionConfigFor(com.fasterxml.jackson.databind.type.LogicalType.Textual);
    for (var input : new com.fasterxml.jackson.databind.cfg.CoercionInputShape[] {
        com.fasterxml.jackson.databind.cfg.CoercionInputShape.Boolean,
        com.fasterxml.jackson.databind.cfg.CoercionInputShape.Integer,
        com.fasterxml.jackson.databind.cfg.CoercionInputShape.Float}) {
      textual.setCoercion(input, com.fasterxml.jackson.databind.cfg.CoercionAction.Fail);
    }
  }

  public WalletDtos.Bundle readBundle(String value) {
    try {
      return proofMapper.readValue(value, WalletDtos.Bundle.class);
    } catch (Exception e) {
      throw new IllegalArgumentException("Malformed v1 proof bundle");
    }
  }

  public String write(Object value) {
    try {
      return mapper.writeValueAsString(value);
    } catch (Exception e) {
      throw new IllegalStateException("Cannot encode wallet data", e);
    }
  }

  public <T> T read(String value, Class<T> type) {
    try {
      return mapper.readValue(value, type);
    } catch (Exception e) {
      throw new IllegalStateException("Cannot decode wallet data", e);
    }
  }
}
