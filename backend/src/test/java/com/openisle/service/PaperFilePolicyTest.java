package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.openisle.dto.PaperSubmissionFilePresignRequest;
import com.openisle.model.PaperFileRole;
import com.openisle.model.PaperFileVisibility;
import org.junit.jupiter.api.Test;

class PaperFilePolicyTest {

  private final PaperFilePolicy policy = new PaperFilePolicy();

  @Test
  void acceptsRequiredSubmissionFileTypes() {
    assertDoesNotThrow(() -> policy.validate(request("paper.docx", 1024, PaperFileRole.MANUSCRIPT)));
    assertDoesNotThrow(() -> policy.validate(request("letter.pdf", 1024, PaperFileRole.COVER_LETTER)));
    assertDoesNotThrow(() -> policy.validate(request("toc.png", 1024, PaperFileRole.TOC_GRAPHIC)));
  }

  @Test
  void rejectsInvalidManuscriptAndOversizedTocGraphic() {
    assertThrows(
      IllegalArgumentException.class,
      () -> policy.validate(request("paper.pdf", 1024, PaperFileRole.MANUSCRIPT))
    );
    assertThrows(
      IllegalArgumentException.class,
      () -> policy.validate(request("toc.png", 11L * 1024 * 1024, PaperFileRole.TOC_GRAPHIC))
    );
  }

  @Test
  void acceptsBrowserFiguresAndRejectsInvalidOrOversizedFigures() {
    assertDoesNotThrow(() -> policy.validate(request("figure.jpg", 1024, PaperFileRole.FIGURE)));
    assertDoesNotThrow(() -> policy.validate(request("figure.webp", 1024, PaperFileRole.FIGURE)));
    assertThrows(
      IllegalArgumentException.class,
      () -> policy.validate(request("figure.tif", 1024, PaperFileRole.FIGURE))
    );
    assertThrows(
      IllegalArgumentException.class,
      () -> policy.validate(request("figure.png", 21L * 1024 * 1024, PaperFileRole.FIGURE))
    );
  }

  @Test
  void forcesPrivateAndPublicRoleVisibility() {
    assertEquals(
      PaperFileVisibility.PRIVATE,
      policy.resolveVisibility(PaperFileRole.COVER_LETTER, PaperFileVisibility.PUBLIC)
    );
    assertEquals(
      PaperFileVisibility.PUBLIC,
      policy.resolveVisibility(PaperFileRole.TOC_GRAPHIC, PaperFileVisibility.PRIVATE)
    );
    assertEquals(
      PaperFileVisibility.PUBLIC,
      policy.resolveVisibility(PaperFileRole.FIGURE, PaperFileVisibility.PRIVATE)
    );
  }

  @Test
  void requiresDescriptionForPublicSupportingInformation() {
    PaperSubmissionFilePresignRequest request = request(
      "supporting.pdf",
      1024,
      PaperFileRole.SUPPORTING_INFORMATION
    );
    request.setVisibility(PaperFileVisibility.PUBLIC);

    assertThrows(IllegalArgumentException.class, () -> policy.validate(request));

    request.setDescription("Experimental methods and additional figures");
    assertDoesNotThrow(() -> policy.validate(request));
  }

  private static PaperSubmissionFilePresignRequest request(
    String filename,
    long size,
    PaperFileRole role
  ) {
    PaperSubmissionFilePresignRequest request = new PaperSubmissionFilePresignRequest();
    request.setFileName(filename);
    request.setFileSize(size);
    request.setRole(role);
    return request;
  }
}
