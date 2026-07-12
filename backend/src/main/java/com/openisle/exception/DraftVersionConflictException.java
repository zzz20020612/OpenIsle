package com.openisle.exception;

import lombok.Getter;

@Getter
public class DraftVersionConflictException extends RuntimeException {

  private final long currentVersion;

  public DraftVersionConflictException(long currentVersion) {
    super("Draft was updated in another session");
    this.currentVersion = currentVersion;
  }
}
