package com.openisle.service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.stereotype.Service;

@Service
public class LocalPresignedUploadService {

  private static final String IMAGE_UPLOAD_DIR = "dynamic_assert";
  private static final String PAPER_MANUSCRIPT_UPLOAD_DIR = "paper_manuscripts";
  private static final String PAPER_SUPPLEMENTARY_UPLOAD_DIR = "paper_supplementary";

  private final Path uploadRoot;
  private final String publicBaseUrl;
  private final Map<String, String> pendingUploads = new ConcurrentHashMap<>();
  private final Map<String, PendingDownload> pendingDownloads = new ConcurrentHashMap<>();

  public LocalPresignedUploadService(
    @Value("${app.upload.local-dir:uploads}") String uploadDir,
    @Value("${app.upload.local-base-url:http://localhost:${server.port:8080}}") String publicBaseUrl
  ) {
    this.uploadRoot = Path.of(uploadDir).toAbsolutePath().normalize();
    this.publicBaseUrl = trimTrailingSlash(publicBaseUrl);
  }

  public Map<String, String> presignUpload(String filename, String purpose) {
    String extension = extensionOf(filename);
    String key = directoryForPurpose(purpose) + "/" + randomName(extension);
    String token = UUID.randomUUID().toString().replace("-", "");
    pendingUploads.put(token, key);
    return Map.of(
      "uploadUrl",
      publicBaseUrl + "/api/upload/local/" + token,
      "fileUrl",
      publicBaseUrl + "/api/upload/local/file/" + key,
      "key",
      key
    );
  }

  public String storeUpload(String token, byte[] data) throws IOException {
    String key = pendingUploads.remove(token);
    if (key == null) {
      throw new IllegalArgumentException("Upload token is invalid or expired");
    }
    Path target = resolveKey(key);
    Files.createDirectories(target.getParent());
    Files.write(target, data);
    return key;
  }

  public String presignDownload(String key, String filename, boolean inline) {
    resolveKey(key);
    String token = UUID.randomUUID().toString().replace("-", "");
    pendingDownloads.put(
      token,
      new PendingDownload(key, safeFilename(filename), inline, Instant.now().plusSeconds(15 * 60))
    );
    return publicBaseUrl + "/api/upload/local/download/" + token;
  }

  public SignedDownload consumeDownload(String token) throws IOException {
    PendingDownload pending = pendingDownloads.remove(token);
    if (pending == null || pending.expiresAt().isBefore(Instant.now())) {
      throw new IllegalArgumentException("Download token is invalid or expired");
    }
    Path file = resolveKey(pending.key());
    if (!Files.exists(file) || !Files.isRegularFile(file)) {
      throw new java.io.FileNotFoundException("File not found");
    }
    String contentType = Files.probeContentType(file);
    return new SignedDownload(
      new UrlResource(file.toUri()),
      pending.filename(),
      contentType == null ? "application/octet-stream" : contentType,
      pending.inline()
    );
  }

  public Resource loadFile(String directory, String filename) throws IOException {
    Path file = resolveKey(directory + "/" + filename);
    if (!Files.exists(file) || !Files.isRegularFile(file)) {
      throw new java.io.FileNotFoundException("File not found");
    }
    return new UrlResource(file.toUri());
  }

  public boolean isPublicDirectory(String directory) {
    return IMAGE_UPLOAD_DIR.equals(directory);
  }

  public String contentType(String directory, String filename) throws IOException {
    String type = Files.probeContentType(resolveKey(directory + "/" + filename));
    return type == null ? "application/octet-stream" : type;
  }

  private Path resolveKey(String key) {
    Path resolved = uploadRoot.resolve(key).normalize();
    if (!resolved.startsWith(uploadRoot)) {
      throw new IllegalArgumentException("Invalid upload path");
    }
    return resolved;
  }

  private static String directoryForPurpose(String purpose) {
    if ("manuscript".equalsIgnoreCase(purpose)) {
      return PAPER_MANUSCRIPT_UPLOAD_DIR;
    }
    if ("supplementary".equalsIgnoreCase(purpose)) {
      return PAPER_SUPPLEMENTARY_UPLOAD_DIR;
    }
    return IMAGE_UPLOAD_DIR;
  }

  private static String extensionOf(String filename) {
    if (filename == null) {
      return "";
    }
    String lower = filename.toLowerCase(Locale.ROOT);
    int dot = lower.lastIndexOf('.');
    return dot < 0 ? "" : lower.substring(dot);
  }

  private static String randomName(String extension) {
    return UUID.randomUUID().toString().replace("-", "") + extension;
  }

  private static String safeFilename(String filename) {
    if (filename == null || filename.isBlank()) {
      return "download";
    }
    String normalized = filename.replace('\\', '/');
    int slash = normalized.lastIndexOf('/');
    return (slash >= 0 ? normalized.substring(slash + 1) : normalized)
      .replace('"', '_')
      .replace('\r', '_')
      .replace('\n', '_');
  }

  private static String trimTrailingSlash(String value) {
    if (value == null || value.isBlank()) {
      return "http://localhost:8080";
    }
    return value.endsWith("/") ? value.substring(0, value.length() - 1) : value;
  }

  private record PendingDownload(
    String key,
    String filename,
    boolean inline,
    Instant expiresAt
  ) {}

  public record SignedDownload(
    Resource resource,
    String filename,
    String contentType,
    boolean inline
  ) {}
}
