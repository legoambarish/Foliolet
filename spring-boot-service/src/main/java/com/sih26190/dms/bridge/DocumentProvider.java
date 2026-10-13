package com.sih26190.dms.bridge;

import java.util.List;
import java.util.Map;

/** Provider transport is separate from cryptographic source classification. */
public interface DocumentProvider {
  String name();

  Map<String, Object> start(String callback) throws Exception;

  boolean authenticated(String session) throws Exception;

  List<Map<String, Object>> list(String session) throws Exception;

  byte[] fetch(String session, Map<String, Object> selection) throws Exception;

  default void cancel(String session) throws Exception {}
}
