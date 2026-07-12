package com.openisle.service;

import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class PresignedFileStorageService {

  private final ImageUploader imageUploader;
  private final LocalPresignedUploadService localUploadService;

  public Map<String, String> presignUpload(String filename, String purpose) {
    try {
      return imageUploader.presignUpload(filename, purpose);
    } catch (IllegalStateException | UnsupportedOperationException exception) {
      return localUploadService.presignUpload(filename, purpose);
    }
  }

  public String presignDownload(String key, String filename, boolean inline) {
    try {
      return imageUploader.presignDownload(key, filename, inline);
    } catch (IllegalStateException | UnsupportedOperationException exception) {
      return localUploadService.presignDownload(key, filename, inline);
    }
  }
}
