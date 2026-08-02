package com.openisle.service;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.openisle.repository.ImageRepository;
import com.qcloud.cos.COSClient;
import com.qcloud.cos.model.PutObjectRequest;
import java.net.MalformedURLException;
import java.net.URL;
import java.util.Map;
import org.junit.jupiter.api.Test;

class CosImageUploaderTest {

  @Test
  void uploadReturnsUrl() {
    COSClient client = mock(COSClient.class);
    ImageRepository repo = mock(ImageRepository.class);
    CosImageUploader uploader = new CosImageUploader(
      client,
      repo,
      "bucket",
      "http://cos.example.com"
    );

    String url = uploader.upload("data".getBytes(), "img.png").join();

    verify(client).putObject(any(PutObjectRequest.class));
    assertTrue(url.matches("http://cos.example.com/dynamic_assert/[a-f0-9]{32}\\.png"));
  }

  @Test
  void presignUploadUsesManuscriptDirectoryForPaperManuscripts() throws MalformedURLException {
    COSClient client = mock(COSClient.class);
    when(client.generatePresignedUrl(any())).thenReturn(new URL("http://upload.example.com/signed"));
    ImageRepository repo = mock(ImageRepository.class);
    CosImageUploader uploader = new CosImageUploader(
      client,
      repo,
      "bucket",
      "http://cos.example.com"
    );

    Map<String, String> result = uploader.presignUpload("paper.pdf", "manuscript");

    assertEquals("http://upload.example.com/signed", result.get("uploadUrl"));
    assertTrue(result.get("fileUrl").matches("http://cos.example.com/paper_manuscripts/[a-f0-9]{32}\\.pdf"));
    assertTrue(result.get("key").matches("paper_manuscripts/[a-f0-9]{32}\\.pdf"));
  }

  @Test
  void presignUploadUsesSupplementaryDirectoryForPaperSupplementaryFiles()
    throws MalformedURLException {
    COSClient client = mock(COSClient.class);
    when(client.generatePresignedUrl(any())).thenReturn(new URL("http://upload.example.com/signed"));
    ImageRepository repo = mock(ImageRepository.class);
    CosImageUploader uploader = new CosImageUploader(
      client,
      repo,
      "bucket",
      "http://cos.example.com"
    );

    Map<String, String> result = uploader.presignUpload("appendix.zip", "supplementary");

    assertTrue(result.get("fileUrl").matches("http://cos.example.com/paper_supplementary/[a-f0-9]{32}\\.zip"));
    assertTrue(result.get("key").matches("paper_supplementary/[a-f0-9]{32}\\.zip"));
  }
}
