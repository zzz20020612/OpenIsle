package com.openisle.service;

import com.openisle.dto.PaperArticleBlockDto;
import com.openisle.dto.PaperArticleDto;
import com.openisle.dto.PaperArticleIssueDto;
import com.openisle.dto.PaperArticleSectionDto;
import com.openisle.dto.PaperArticleValidationDto;
import com.openisle.model.PaperFileRole;
import com.openisle.model.PaperSubmissionFile;
import com.openisle.model.PaperUploadStatus;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import org.springframework.stereotype.Component;

@Component
public class PaperArticleValidator {

  private static final Set<String> BLOCK_TYPES = Set.of(
    "PARAGRAPH",
    "SUBHEADING",
    "FIGURE",
    "EQUATION",
    "TABLE"
  );

  public PaperArticleValidationDto validate(
    PaperArticleDto article,
    List<PaperSubmissionFile> draftFiles
  ) {
    PaperArticleValidationDto result = new PaperArticleValidationDto();
    List<PaperArticleSectionDto> sections = article == null ? null : article.getSections();
    if (sections == null || sections.isEmpty()) {
      add(result, null, null, "sections", "ARTICLE_SECTION_REQUIRED", "Add at least one article section.");
      return finish(result);
    }

    Set<String> knownSectionKeys = new HashSet<>();
    sections.stream().filter(Objects::nonNull).map(PaperArticleSectionDto::getKey).filter(this::present).forEach(knownSectionKeys::add);
    Set<String> seenSectionKeys = new HashSet<>();
    Set<String> seenBlockKeys = new HashSet<>();
    boolean hasParagraph = false;

    for (PaperArticleSectionDto section : sections) {
      if (section == null) {
        add(result, null, null, "section", "ARTICLE_SECTION_INVALID", "Remove the invalid article section.");
        continue;
      }
      String sectionKey = clean(section.getKey());
      if (sectionKey == null) {
        add(result, null, null, "key", "SECTION_KEY_REQUIRED", "The section is missing its stable key.");
      } else if (!seenSectionKeys.add(sectionKey)) {
        add(result, sectionKey, null, "key", "DUPLICATE_SECTION_KEY", "Each section must have a unique key.");
      }
      if (!present(section.getHeading())) {
        add(result, sectionKey, null, "heading", "SECTION_HEADING_REQUIRED", "Enter a section heading.");
      }
      if (section.getLevel() < 1 || section.getLevel() > 3) {
        add(result, sectionKey, null, "level", "SECTION_LEVEL_INVALID", "Section level must be between 1 and 3.");
      }
      if (present(section.getParentKey()) && !knownSectionKeys.contains(section.getParentKey().trim())) {
        add(result, sectionKey, null, "parentKey", "UNKNOWN_PARENT_SECTION", "Select an existing parent section.");
      }

      List<PaperArticleBlockDto> blocks = section.getBlocks();
      if (blocks == null) continue;
      for (PaperArticleBlockDto block : blocks) {
        if (block == null) {
          add(result, sectionKey, null, "block", "ARTICLE_BLOCK_INVALID", "Remove the invalid article block.");
          continue;
        }
        String blockKey = clean(block.getKey());
        if (blockKey == null) {
          add(result, sectionKey, null, "key", "BLOCK_KEY_REQUIRED", "The block is missing its stable key.");
        } else if (!seenBlockKeys.add(blockKey)) {
          add(result, sectionKey, blockKey, "key", "DUPLICATE_BLOCK_KEY", "Each article block must have a unique key.");
        }
        String type = clean(block.getType());
        if (type == null || !BLOCK_TYPES.contains(type)) {
          add(result, sectionKey, blockKey, "type", "BLOCK_TYPE_INVALID", "Select a supported article block type.");
          continue;
        }
        switch (type) {
          case "PARAGRAPH" -> {
            if (!present(block.getText())) {
              add(result, sectionKey, blockKey, "text", "PARAGRAPH_TEXT_REQUIRED", "Enter paragraph text.");
            } else {
              hasParagraph = true;
            }
          }
          case "SUBHEADING" -> {
            if (!present(block.getText())) {
              add(result, sectionKey, blockKey, "text", "SUBHEADING_TEXT_REQUIRED", "Enter the subheading text.");
            }
          }
          case "EQUATION" -> {
            if (!present(block.getLatex())) {
              add(result, sectionKey, blockKey, "latex", "EQUATION_LATEX_REQUIRED", "Enter the equation in LaTeX.");
            }
          }
          case "FIGURE" -> validateFigure(block, sectionKey, blockKey, draftFiles, result);
          case "TABLE" -> validateTable(block, sectionKey, blockKey, result);
          default -> throw new IllegalStateException("Unsupported block type " + type);
        }
      }
    }

    if (!hasParagraph) {
      add(result, null, null, "sections", "ARTICLE_PARAGRAPH_REQUIRED", "Add at least one non-empty paragraph.");
    }
    return finish(result);
  }

  private void validateFigure(
    PaperArticleBlockDto block,
    String sectionKey,
    String blockKey,
    List<PaperSubmissionFile> draftFiles,
    PaperArticleValidationDto result
  ) {
    if (block.getFileId() == null) {
      add(result, sectionKey, blockKey, "fileId", "FIGURE_FILE_REQUIRED", "Upload a figure image.");
    } else {
      boolean available = draftFiles != null && draftFiles.stream().anyMatch(file ->
        file != null &&
        block.getFileId().equals(file.getId()) &&
        file.getRole() == PaperFileRole.FIGURE &&
        file.getUploadStatus() == PaperUploadStatus.UPLOADED
      );
      if (!available) {
        add(result, sectionKey, blockKey, "fileId", "FIGURE_FILE_UNAVAILABLE", "The referenced figure is not available.");
      }
    }
    if (!present(block.getCaption())) {
      add(result, sectionKey, blockKey, "caption", "FIGURE_CAPTION_REQUIRED", "Enter a figure caption.");
    }
    if (!present(block.getAltText())) {
      add(result, sectionKey, blockKey, "altText", "FIGURE_ALT_TEXT_REQUIRED", "Describe the figure for accessible reading.");
    }
  }

  private void validateTable(
    PaperArticleBlockDto block,
    String sectionKey,
    String blockKey,
    PaperArticleValidationDto result
  ) {
    boolean hasColumns = block.getColumns() != null && block.getColumns().stream().anyMatch(this::present);
    boolean hasRows = block.getRows() != null && block.getRows().stream().filter(Objects::nonNull).flatMap(List::stream).anyMatch(this::present);
    if (!hasColumns || !hasRows) {
      add(result, sectionKey, blockKey, "rows", "TABLE_CONTENT_REQUIRED", "Add table columns and at least one data row.");
    }
    if (!present(block.getCaption())) {
      add(result, sectionKey, blockKey, "caption", "TABLE_CAPTION_REQUIRED", "Enter a table caption.");
    }
  }

  private PaperArticleValidationDto finish(PaperArticleValidationDto result) {
    result.setValid(result.getIssues().isEmpty());
    return result;
  }

  private void add(
    PaperArticleValidationDto result,
    String sectionKey,
    String blockKey,
    String field,
    String code,
    String message
  ) {
    result.getIssues().add(new PaperArticleIssueDto(sectionKey, blockKey, field, code, message));
  }

  private boolean present(String value) {
    return clean(value) != null;
  }

  private String clean(String value) {
    return value == null || value.isBlank() ? null : value.trim();
  }
}
