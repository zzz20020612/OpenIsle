package com.openisle.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.openisle.model.LiteratureAdminAuditLog;
import com.openisle.repository.LiteratureAdminAuditLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class LiteratureAdminAuditService {
  private final LiteratureAdminAuditLogRepository repository;

  public void record(String actor, String method, String operation, JsonNode request, int status, String remoteAddress) {
    LiteratureAdminAuditLog log = new LiteratureAdminAuditLog();
    log.setActorUsername(actor);
    log.setMethod(method);
    log.setOperation(operation);
    log.setRequestSummary(sanitize(request));
    log.setSuccessful(status >= 200 && status < 400);
    log.setUpstreamStatus(status);
    log.setRemoteAddress(remoteAddress);
    repository.save(log);
  }

  private String sanitize(JsonNode value) {
    if (value == null || value.isNull()) return null;
    JsonNode copy = value.deepCopy();
    redact(copy);
    String result = copy.toString();
    return result.length() <= 8000 ? result : result.substring(0, 8000);
  }

  private void redact(JsonNode node) {
    if (node == null) return;
    if (node.isObject()) {
      node.fields().forEachRemaining(entry -> {
        String key = entry.getKey().toLowerCase();
        if (key.contains("key") || key.contains("token") || key.contains("secret") || key.contains("password")) {
          ((ObjectNode) node).put(entry.getKey(), "[REDACTED]");
        } else redact(entry.getValue());
      });
    } else if (node.isArray()) node.forEach(this::redact);
  }
}
