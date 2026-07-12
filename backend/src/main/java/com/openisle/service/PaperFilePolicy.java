package com.openisle.service;

import com.openisle.dto.PaperSubmissionFilePresignRequest;
import com.openisle.model.PaperFileRole;
import com.openisle.model.PaperFileVisibility;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Service;

@Service
public class PaperFilePolicy {

  private static final long MB = 1024L * 1024L;
  private static final Set<String> DOCUMENTS = Set.of("doc", "docx", "pdf", "rtf", "txt");
  private static final Set<String> IMAGES = Set.of("png", "jpg", "jpeg", "webp", "gif");
  private static final Set<String> SUPPORTING = Set.of(
    "pdf",
    "doc",
    "docx",
    "xlsx",
    "csv",
    "zip",
    "txt",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "tex",
    "bib",
    "json"
  );
  private static final Set<String> CODE_EXTENSIONS = Set.of(
    "zip",
    "txt",
    "md",
    "py",
    "r",
    "js",
    "ts",
    "ipynb"
  );

  private static final Map<PaperFileRole, Long> MAX_BYTES = Map.ofEntries(
    Map.entry(PaperFileRole.MANUSCRIPT, 50 * MB),
    Map.entry(PaperFileRole.COVER_LETTER, 20 * MB),
    Map.entry(PaperFileRole.TOC_GRAPHIC, 10 * MB),
    Map.entry(PaperFileRole.SUPPORTING_INFORMATION, 100 * MB),
    Map.entry(PaperFileRole.REVIEW_ONLY, 100 * MB),
    Map.entry(PaperFileRole.PDF_VERSION, 100 * MB),
    Map.entry(PaperFileRole.LATEX_SOURCE, 100 * MB),
    Map.entry(PaperFileRole.DATASET, 100 * MB),
    Map.entry(PaperFileRole.CODE, 100 * MB),
    Map.entry(PaperFileRole.OTHER, 100 * MB)
  );

  public void validate(PaperSubmissionFilePresignRequest request) {
    if (request == null || request.getRole() == null) {
      throw new IllegalArgumentException("File role is required");
    }
    if (request.getFileName() == null || request.getFileName().isBlank()) {
      throw new IllegalArgumentException("File name is required");
    }
    if (request.getFileSize() <= 0 || request.getFileSize() > MAX_BYTES.get(request.getRole())) {
      throw new IllegalArgumentException("File exceeds the size limit for this role");
    }
    String extension = extension(request.getFileName());
    if (!allowedExtensions(request.getRole()).contains(extension)) {
      throw new IllegalArgumentException("File type is not allowed for this role");
    }
    if (
      request.getRole() == PaperFileRole.SUPPORTING_INFORMATION &&
      resolveVisibility(request.getRole(), request.getVisibility()) == PaperFileVisibility.PUBLIC &&
      (request.getDescription() == null || request.getDescription().isBlank())
    ) {
      throw new IllegalArgumentException(
        "A public Supporting Information file requires a description"
      );
    }
  }

  public PaperFileVisibility resolveVisibility(
    PaperFileRole role,
    PaperFileVisibility requested
  ) {
    if (role == PaperFileRole.COVER_LETTER || role == PaperFileRole.REVIEW_ONLY) {
      return PaperFileVisibility.PRIVATE;
    }
    if (role == PaperFileRole.MANUSCRIPT || role == PaperFileRole.TOC_GRAPHIC) {
      return PaperFileVisibility.PUBLIC;
    }
    return requested != null ? requested : PaperFileVisibility.PRIVATE;
  }

  public String storagePurpose(PaperFileRole role) {
    if (role == PaperFileRole.TOC_GRAPHIC) {
      return "image";
    }
    if (
      role == PaperFileRole.SUPPORTING_INFORMATION ||
      role == PaperFileRole.DATASET ||
      role == PaperFileRole.CODE ||
      role == PaperFileRole.OTHER
    ) {
      return "supplementary";
    }
    return "manuscript";
  }

  private Set<String> allowedExtensions(PaperFileRole role) {
    return switch (role) {
      case MANUSCRIPT -> Set.of("docx");
      case COVER_LETTER -> DOCUMENTS;
      case TOC_GRAPHIC -> IMAGES;
      case PDF_VERSION -> Set.of("pdf");
      case LATEX_SOURCE -> Set.of("tex", "bib", "zip");
      case DATASET -> Set.of("csv", "xlsx", "json", "zip");
      case CODE -> CODE_EXTENSIONS;
      case SUPPORTING_INFORMATION, REVIEW_ONLY, OTHER -> SUPPORTING;
    };
  }

  private String extension(String filename) {
    String lower = filename.toLowerCase(Locale.ROOT);
    int dot = lower.lastIndexOf('.');
    return dot >= 0 ? lower.substring(dot + 1) : "";
  }
}
