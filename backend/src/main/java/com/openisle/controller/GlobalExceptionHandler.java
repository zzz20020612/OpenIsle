package com.openisle.controller;

import com.openisle.exception.FieldException;
import com.openisle.exception.DraftVersionConflictException;
import com.openisle.exception.NotFoundException;
import com.openisle.exception.RateLimitException;
import java.util.Map;
import org.springframework.dao.OptimisticLockingFailureException;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

  @ExceptionHandler(DraftVersionConflictException.class)
  public ResponseEntity<?> handleDraftVersionConflict(DraftVersionConflictException ex) {
    return ResponseEntity
      .status(409)
      .body(Map.of("error", ex.getMessage(), "currentVersion", ex.getCurrentVersion()));
  }

  @ExceptionHandler(OptimisticLockingFailureException.class)
  public ResponseEntity<?> handleOptimisticLockingFailure(OptimisticLockingFailureException ex) {
    return ResponseEntity
      .status(409)
      .body(Map.of("error", "Draft was updated in another session"));
  }

  @ExceptionHandler(AccessDeniedException.class)
  public ResponseEntity<?> handleAccessDenied(AccessDeniedException ex) {
    return ResponseEntity.status(403).body(Map.of("error", ex.getMessage()));
  }

  @ExceptionHandler(FieldException.class)
  public ResponseEntity<?> handleFieldException(FieldException ex) {
    return ResponseEntity.badRequest().body(
      Map.of("error", ex.getMessage(), "field", ex.getField())
    );
  }

  @ExceptionHandler(NotFoundException.class)
  public ResponseEntity<?> handleNotFoundException(NotFoundException ex) {
    return ResponseEntity.status(404).body(Map.of("error", ex.getMessage()));
  }

  @ExceptionHandler(RateLimitException.class)
  public ResponseEntity<?> handleRateLimitException(RateLimitException ex) {
    return ResponseEntity.status(429).body(Map.of("error", ex.getMessage()));
  }

  @ExceptionHandler(Exception.class)
  public ResponseEntity<?> handleException(Exception ex) {
    String message = ex.getMessage();
    if (message == null) {
      message = ex.getClass().getSimpleName();
    }
    return ResponseEntity.badRequest().body(Map.of("error", message));
  }
}
