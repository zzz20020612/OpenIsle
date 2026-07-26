package com.openisle.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.openisle.dto.PaperArticleBlockDto;
import com.openisle.dto.PaperArticleDto;
import com.openisle.dto.PaperArticleSectionDto;
import com.openisle.dto.PaperArticleValidationDto;
import com.openisle.model.PaperFileRole;
import com.openisle.model.PaperSubmissionFile;
import com.openisle.model.PaperUploadStatus;
import java.util.List;
import org.junit.jupiter.api.Test;

class PaperArticleValidatorTest {

  private final PaperArticleValidator validator = new PaperArticleValidator();

  @Test
  void rejectsArticleWithoutSections() {
    PaperArticleValidationDto result = validator.validate(new PaperArticleDto(), List.of());

    assertFalse(result.isValid());
    assertEquals("ARTICLE_SECTION_REQUIRED", result.getIssues().get(0).getCode());
  }

  @Test
  void reportsDuplicateKeysAndInvalidHierarchyInStableOrder() {
    PaperArticleDto article = new PaperArticleDto();
    PaperArticleSectionDto first = section("same", null, 1, paragraph("duplicate", "Text"));
    PaperArticleSectionDto second = section("same", "missing-parent", 2, paragraph("duplicate", "Text"));
    article.setSections(List.of(first, second));

    PaperArticleValidationDto result = validator.validate(article, List.of());

    assertFalse(result.isValid());
    assertEquals(
      List.of("DUPLICATE_SECTION_KEY", "UNKNOWN_PARENT_SECTION", "DUPLICATE_BLOCK_KEY"),
      result.getIssues().stream().map(issue -> issue.getCode()).toList()
    );
  }

  @Test
  void rejectsEmptyParagraphEquationFigureAndTable() {
    PaperArticleDto article = new PaperArticleDto();
    PaperArticleBlockDto paragraph = paragraph("paragraph", " ");
    PaperArticleBlockDto equation = block("equation", "EQUATION");
    PaperArticleBlockDto figure = block("figure", "FIGURE");
    PaperArticleBlockDto table = block("table", "TABLE");
    article.setSections(List.of(section("results", null, 1, paragraph, equation, figure, table)));

    PaperArticleValidationDto result = validator.validate(article, List.of());

    assertFalse(result.isValid());
    assertTrue(result.getIssues().stream().anyMatch(issue -> issue.getCode().equals("PARAGRAPH_TEXT_REQUIRED")));
    assertTrue(result.getIssues().stream().anyMatch(issue -> issue.getCode().equals("EQUATION_LATEX_REQUIRED")));
    assertTrue(result.getIssues().stream().anyMatch(issue -> issue.getCode().equals("FIGURE_FILE_REQUIRED")));
    assertTrue(result.getIssues().stream().anyMatch(issue -> issue.getCode().equals("FIGURE_CAPTION_REQUIRED")));
    assertTrue(result.getIssues().stream().anyMatch(issue -> issue.getCode().equals("FIGURE_ALT_TEXT_REQUIRED")));
    assertTrue(result.getIssues().stream().anyMatch(issue -> issue.getCode().equals("TABLE_CONTENT_REQUIRED")));
  }

  @Test
  void rejectsFigureThatIsNotAnUploadedDraftFigure() {
    PaperArticleDto article = validArticle(41L);
    PaperSubmissionFile manuscript = file(41L, PaperFileRole.MANUSCRIPT, PaperUploadStatus.UPLOADED);

    PaperArticleValidationDto result = validator.validate(article, List.of(manuscript));

    assertFalse(result.isValid());
    assertTrue(result.getIssues().stream().anyMatch(issue -> issue.getCode().equals("FIGURE_FILE_UNAVAILABLE")));
  }

  @Test
  void acceptsCompleteStructuredArticle() {
    PaperArticleDto article = validArticle(41L);
    PaperSubmissionFile figure = file(41L, PaperFileRole.FIGURE, PaperUploadStatus.UPLOADED);

    PaperArticleValidationDto result = validator.validate(article, List.of(figure));

    assertTrue(result.isValid());
    assertTrue(result.getIssues().isEmpty());
  }

  private PaperArticleDto validArticle(Long figureId) {
    PaperArticleDto article = new PaperArticleDto();
    PaperArticleBlockDto paragraph = paragraph("paragraph-1", "The model conserves total mass.");
    PaperArticleBlockDto equation = block("equation-1", "EQUATION");
    equation.setLatex("X_{ij}=V_{ij}/\\sum V_{ij}");
    equation.setLabel("eq-normalization");
    PaperArticleBlockDto figure = block("figure-1", "FIGURE");
    figure.setFileId(figureId);
    figure.setLabel("fig-study-area");
    figure.setCaption("Overview of the study area.");
    figure.setAltText("Map of the Erhai Lake Basin study area.");
    PaperArticleBlockDto table = block("table-1", "TABLE");
    table.setCaption("Model performance.");
    table.setColumns(List.of("Pollutant", "R2"));
    table.setRows(List.of(List.of("COD", "0.98")));
    article.setSections(List.of(section("introduction", null, 1, paragraph, equation, figure, table)));
    return article;
  }

  private PaperArticleSectionDto section(
    String key,
    String parentKey,
    int level,
    PaperArticleBlockDto... blocks
  ) {
    PaperArticleSectionDto section = new PaperArticleSectionDto();
    section.setKey(key);
    section.setParentKey(parentKey);
    section.setHeading("Section " + key);
    section.setLevel(level);
    section.setBlocks(List.of(blocks));
    return section;
  }

  private PaperArticleBlockDto paragraph(String key, String text) {
    PaperArticleBlockDto block = block(key, "PARAGRAPH");
    block.setText(text);
    return block;
  }

  private PaperArticleBlockDto block(String key, String type) {
    PaperArticleBlockDto block = new PaperArticleBlockDto();
    block.setKey(key);
    block.setType(type);
    return block;
  }

  private PaperSubmissionFile file(Long id, PaperFileRole role, PaperUploadStatus status) {
    PaperSubmissionFile file = new PaperSubmissionFile();
    file.setId(id);
    file.setRole(role);
    file.setUploadStatus(status);
    return file;
  }
}
