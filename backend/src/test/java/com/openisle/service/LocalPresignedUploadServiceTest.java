package com.openisle.service;

import static org.junit.jupiter.api.Assertions.*;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class LocalPresignedUploadServiceTest {

  @TempDir
  Path tempDir;

  @Test
  void presignUploadStoresPaperManuscriptLocally() throws Exception {
    LocalPresignedUploadService service = new LocalPresignedUploadService(
      tempDir.toString(),
      "http://localhost:8080"
    );

    Map<String, String> presign = service.presignUpload("paper.pdf", "manuscript");
    String uploadUrl = presign.get("uploadUrl");
    String fileUrl = presign.get("fileUrl");
    String key = presign.get("key");

    assertTrue(uploadUrl.startsWith("http://localhost:8080/api/upload/local/"));
    assertTrue(fileUrl.matches("http://localhost:8080/api/upload/local/file/paper_manuscripts/[a-f0-9]{32}\\.pdf"));
    assertTrue(key.matches("paper_manuscripts/[a-f0-9]{32}\\.pdf"));

    service.storeUpload(uploadUrl.substring(uploadUrl.lastIndexOf('/') + 1), "data".getBytes());

    assertEquals("data", Files.readString(tempDir.resolve(key)));
  }

  @Test
  void signedDownloadIsShortLivedAndSingleUse() throws Exception {
    LocalPresignedUploadService service = new LocalPresignedUploadService(
      tempDir.toString(),
      "http://localhost:8080"
    );
    Map<String, String> upload = service.presignUpload("supporting.pdf", "supplementary");
    String uploadToken = upload.get("uploadUrl").substring(upload.get("uploadUrl").lastIndexOf('/') + 1);
    service.storeUpload(uploadToken, "supplement".getBytes());

    String downloadUrl = service.presignDownload(
      upload.get("key"),
      "Supporting Information.pdf",
      true
    );
    String downloadToken = downloadUrl.substring(downloadUrl.lastIndexOf('/') + 1);
    LocalPresignedUploadService.SignedDownload download = service.consumeDownload(downloadToken);

    assertTrue(download.inline());
    assertEquals("Supporting Information.pdf", download.filename());
    assertArrayEquals("supplement".getBytes(), download.resource().getInputStream().readAllBytes());
    assertThrows(IllegalArgumentException.class, () -> service.consumeDownload(downloadToken));
  }
}
