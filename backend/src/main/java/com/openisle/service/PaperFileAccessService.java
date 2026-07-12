package com.openisle.service;

import com.openisle.exception.NotFoundException;
import com.openisle.model.PaperFile;
import com.openisle.model.PaperFileVisibility;
import com.openisle.model.PaperProfile;
import com.openisle.model.Role;
import com.openisle.model.User;
import com.openisle.repository.PaperFileRepository;
import com.openisle.repository.PaperProfileRepository;
import com.openisle.repository.UserRepository;
import java.util.Locale;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class PaperFileAccessService {

  private final PaperProfileRepository paperProfileRepository;
  private final PaperFileRepository paperFileRepository;
  private final UserRepository userRepository;
  private final PaperAccessPolicy paperAccessPolicy;
  private final PresignedFileStorageService storageService;

  @Transactional
  public String openFile(
    Long paperId,
    Long fileId,
    String mode,
    String viewerUsername
  ) {
    PaperProfile paper = paperProfileRepository
      .findById(paperId)
      .orElseThrow(() -> new NotFoundException("Paper not found"));
    PaperFile file = paperFileRepository
      .findByIdAndPaperId(fileId, paperId)
      .orElseThrow(() -> new NotFoundException("Paper file not found"));
    User viewer = viewerUsername == null
      ? null
      : userRepository.findByUsername(viewerUsername).orElse(null);

    boolean publicAccess =
      file.getVisibility() == PaperFileVisibility.PUBLIC &&
      paperAccessPolicy.canAppearInFeed(paper);
    boolean privilegedAccess = canAccessPrivateFiles(viewer, paper);
    if (!publicAccess && !privilegedAccess) {
      throw new AccessDeniedException("You do not have access to this paper file");
    }

    String normalizedMode = mode == null ? "download" : mode.trim().toLowerCase(Locale.ROOT);
    boolean preview;
    if ("preview".equals(normalizedMode)) {
      preview = true;
    } else if ("download".equals(normalizedMode)) {
      preview = false;
    } else {
      throw new IllegalArgumentException("File mode must be preview or download");
    }
    if (preview && !isPreviewable(file.getContentType(), file.getOriginalFileName())) {
      throw new IllegalArgumentException("This file type cannot be previewed online");
    }

    if (preview) {
      paperFileRepository.incrementViewCount(file.getId());
    } else {
      paperFileRepository.incrementDownloadCount(file.getId());
    }
    return storageService.presignDownload(
      file.getStorageKey(),
      file.getDisplayName(),
      preview
    );
  }

  public boolean canAccessPrivateFiles(User user, PaperProfile paper) {
    if (user == null || paper == null) {
      return false;
    }
    return user.getRole() == Role.ADMIN || paperAccessPolicy.isPaperAuthor(user, paper);
  }

  public static boolean isPreviewable(String contentType, String filename) {
    String normalizedType = contentType == null
      ? ""
      : contentType.trim().toLowerCase(Locale.ROOT);
    if (normalizedType.equals("application/pdf") || normalizedType.startsWith("image/")) {
      return true;
    }
    String normalizedName = filename == null ? "" : filename.toLowerCase(Locale.ROOT);
    return normalizedName.endsWith(".pdf") ||
      normalizedName.endsWith(".png") ||
      normalizedName.endsWith(".jpg") ||
      normalizedName.endsWith(".jpeg") ||
      normalizedName.endsWith(".webp") ||
      normalizedName.endsWith(".gif");
  }
}
