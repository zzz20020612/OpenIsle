package com.openisle.controller;

import com.openisle.service.ImageUploader;
import com.openisle.service.LocalPresignedUploadService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.net.URI;
import java.net.URL;
import java.net.URLConnection;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/upload")
@RequiredArgsConstructor
public class UploadController {

  private final ImageUploader imageUploader;
  private final LocalPresignedUploadService localUploadService;
  private static final Set<String> IMAGE_EXTENSIONS = Set.of(
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg"
  );
  private static final Set<String> PAPER_FILE_EXTENSIONS = Set.of(
    ".pdf",
    ".doc",
    ".docx",
    ".tex",
    ".md",
    ".zip",
    ".csv",
    ".xlsx"
  );

  @Value("${app.upload.check-type:true}")
  private boolean checkImageType;

  @Value("${app.upload.max-size:5242880}")
  private long maxUploadSize;

  @PostMapping
  @Operation(summary = "Upload file", description = "Upload image file")
  @ApiResponse(
    responseCode = "200",
    description = "Upload result",
    content = @Content(schema = @Schema(implementation = java.util.Map.class))
  )
  public ResponseEntity<?> upload(@RequestParam("file") MultipartFile file) {
    if (
      checkImageType &&
      (file.getContentType() == null || !file.getContentType().startsWith("image/"))
    ) {
      return ResponseEntity.badRequest().body(Map.of("code", 1, "msg", "File is not an image"));
    }
    if (file.getSize() > maxUploadSize) {
      return ResponseEntity.badRequest().body(Map.of("code", 2, "msg", "File too large"));
    }
    String url;
    try {
      url = imageUploader.upload(file.getBytes(), file.getOriginalFilename()).join();
    } catch (IOException e) {
      return ResponseEntity.internalServerError().body(Map.of("code", 3, "msg", "Upload failed"));
    }
    return ResponseEntity.ok(Map.of("code", 0, "msg", "ok", "data", Map.of("url", url)));
  }

  @PostMapping("/url")
  @Operation(summary = "Upload from URL", description = "Upload image from remote URL")
  @ApiResponse(
    responseCode = "200",
    description = "Upload result",
    content = @Content(schema = @Schema(implementation = java.util.Map.class))
  )
  public ResponseEntity<?> uploadUrl(@RequestBody Map<String, String> body) {
    String link = body.get("url");
    if (link == null || link.isBlank()) {
      return ResponseEntity.badRequest().body(Map.of("code", 1, "msg", "Missing url"));
    }
    try {
      URL u = URI.create(link).toURL();
      byte[] data = u.openStream().readAllBytes();
      if (data.length > maxUploadSize) {
        return ResponseEntity.badRequest().body(Map.of("code", 2, "msg", "File too large"));
      }
      String filename = link.substring(link.lastIndexOf('/') + 1);
      String contentType = URLConnection.guessContentTypeFromStream(new ByteArrayInputStream(data));
      if (checkImageType && (contentType == null || !contentType.startsWith("image/"))) {
        return ResponseEntity.badRequest().body(Map.of("code", 1, "msg", "File is not an image"));
      }
      String url = imageUploader.upload(data, filename).join();
      return ResponseEntity.ok(Map.of("code", 0, "msg", "ok", "data", Map.of("url", url)));
    } catch (Exception e) {
      return ResponseEntity.internalServerError().body(Map.of("code", 3, "msg", "Upload failed"));
    }
  }

  @GetMapping("/presign")
  @Operation(summary = "Presign upload", description = "Get presigned upload URL")
  @ApiResponse(
    responseCode = "200",
    description = "Presigned URL",
    content = @Content(schema = @Schema(implementation = java.util.Map.class))
  )
  public ResponseEntity<?> presign(
    @RequestParam("filename") String filename,
    @RequestParam(value = "purpose", defaultValue = "image") String purpose
  ) {
    String normalizedPurpose = normalizePurpose(purpose);
    if (!isAllowedPresignFile(filename, normalizedPurpose)) {
      return ResponseEntity
        .badRequest()
        .body(Map.of("code", 1, "msg", "File type is not allowed for upload purpose"));
    }
    try {
      return ResponseEntity.ok(imageUploader.presignUpload(filename, normalizedPurpose));
    } catch (IllegalStateException exception) {
      return ResponseEntity.ok(localUploadService.presignUpload(filename, normalizedPurpose));
    }
  }

  @PutMapping("/local/{token}")
  @Operation(summary = "Upload local presigned file", description = "Development local upload target")
  public ResponseEntity<?> uploadLocal(
    @PathVariable String token,
    @RequestBody byte[] data
  ) throws IOException {
    String key = localUploadService.storeUpload(token, data);
    return ResponseEntity.ok(Map.of("code", 0, "msg", "ok", "key", key));
  }

  @GetMapping("/local/file/{directory}/{filename:.+}")
  @Operation(summary = "Get local uploaded file", description = "Development local uploaded file")
  public ResponseEntity<Resource> getLocalFile(
    @PathVariable String directory,
    @PathVariable String filename
  ) throws IOException {
    if (!localUploadService.isPublicDirectory(directory)) {
      return ResponseEntity.notFound().build();
    }
    Resource file = localUploadService.loadFile(directory, filename);
    String contentType = localUploadService.contentType(directory, filename);
    return ResponseEntity
      .ok()
      .contentType(MediaType.parseMediaType(contentType))
      .header(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + filename + "\"")
      .body(file);
  }

  @GetMapping("/local/download/{token}")
  @Operation(summary = "Download a signed local file", description = "Development signed download target")
  public ResponseEntity<Resource> downloadLocal(@PathVariable String token) throws IOException {
    LocalPresignedUploadService.SignedDownload download = localUploadService.consumeDownload(token);
    String disposition = download.inline() ? "inline" : "attachment";
    return ResponseEntity
      .ok()
      .contentType(MediaType.parseMediaType(download.contentType()))
      .header(
        HttpHeaders.CONTENT_DISPOSITION,
        disposition + "; filename=\"" + download.filename() + "\""
      )
      .header(HttpHeaders.CACHE_CONTROL, "private, no-store")
      .body(download.resource());
  }

  private static String normalizePurpose(String purpose) {
    if (purpose == null || purpose.isBlank()) {
      return "image";
    }
    return purpose.trim().toLowerCase(Locale.ROOT);
  }

  private static boolean isAllowedPresignFile(String filename, String purpose) {
    if (filename == null || filename.isBlank()) {
      return false;
    }
    String lower = filename.toLowerCase(Locale.ROOT);
    int dot = lower.lastIndexOf('.');
    if (dot < 0) {
      return false;
    }
    String extension = lower.substring(dot);
    if ("manuscript".equals(purpose) || "supplementary".equals(purpose)) {
      return PAPER_FILE_EXTENSIONS.contains(extension);
    }
    if ("image".equals(purpose)) {
      return IMAGE_EXTENSIONS.contains(extension);
    }
    return false;
  }
}
