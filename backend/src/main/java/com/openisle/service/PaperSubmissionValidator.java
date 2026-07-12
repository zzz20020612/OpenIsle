package com.openisle.service;

import com.openisle.dto.PaperAffiliationRequest;
import com.openisle.dto.PaperAuthorRequest;
import com.openisle.dto.PaperFundingRequest;
import com.openisle.dto.PaperSubmissionIssueDto;
import com.openisle.dto.PaperSubmissionSubmitRequest;
import com.openisle.dto.PaperSubmissionValidationDto;
import com.openisle.dto.PaperSubmitRequest;
import com.openisle.model.PaperFileRole;
import com.openisle.model.PaperFileVisibility;
import com.openisle.model.PaperSubmissionFile;
import com.openisle.model.PaperUploadStatus;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import org.springframework.stereotype.Service;

@Service
public class PaperSubmissionValidator {

  public PaperSubmissionValidationDto validateDraft(
    PaperSubmitRequest form,
    List<PaperSubmissionFile> files
  ) {
    return validate(form, files, null);
  }

  public PaperSubmissionValidationDto validateForSubmission(
    PaperSubmitRequest form,
    List<PaperSubmissionFile> files,
    PaperSubmissionSubmitRequest confirmations
  ) {
    return validate(form, files, confirmations);
  }

  private PaperSubmissionValidationDto validate(
    PaperSubmitRequest form,
    List<PaperSubmissionFile> files,
    PaperSubmissionSubmitRequest confirmations
  ) {
    List<PaperSubmissionIssueDto> issues = new ArrayList<>();
    PaperSubmitRequest safeForm = form != null ? form : new PaperSubmitRequest();
    List<PaperSubmissionFile> safeFiles = files != null ? files : List.of();

    validateManuscriptType(safeForm, issues);
    validateFiles(safeFiles, issues);
    validateMetadata(safeForm, issues);
    validateAuthors(safeForm.getAuthors(), issues);
    validateFunding(safeForm, issues);
    validateDeclarations(safeForm, confirmations, issues);

    return new PaperSubmissionValidationDto(issues.isEmpty(), List.copyOf(issues));
  }

  private void validateManuscriptType(
    PaperSubmitRequest form,
    List<PaperSubmissionIssueDto> issues
  ) {
    String paperType = clean(form.getPaperType());
    if (!"Research Article".equals(paperType) && !"Review".equals(paperType)) {
      add(
        issues,
        "manuscript-type",
        "paperType",
        "UNSUPPORTED_MANUSCRIPT_TYPE",
        "Select Research Article or Review."
      );
    }
  }

  private void validateFiles(
    List<PaperSubmissionFile> files,
    List<PaperSubmissionIssueDto> issues
  ) {
    List<PaperSubmissionFile> uploadedFiles = files
      .stream()
      .filter(Objects::nonNull)
      .filter(file -> file.getUploadStatus() == PaperUploadStatus.UPLOADED)
      .toList();

    requireExactlyOneRole(uploadedFiles, PaperFileRole.MANUSCRIPT, "Manuscript File", issues);
    requireExactlyOneRole(uploadedFiles, PaperFileRole.COVER_LETTER, "Cover Letter", issues);
    requireExactlyOneRole(uploadedFiles, PaperFileRole.TOC_GRAPHIC, "TOC Graphic", issues);

    uploadedFiles
      .stream()
      .filter(file -> file.getRole() == PaperFileRole.MANUSCRIPT)
      .filter(file -> !extension(file.getOriginalFileName()).equals("docx"))
      .forEach(file ->
        add(
          issues,
          "file-upload",
          "files." + file.getId(),
          "MANUSCRIPT_MUST_BE_DOCX",
          "The manuscript file must be a DOCX document."
        )
      );

    for (PaperSubmissionFile file : uploadedFiles) {
      if (
        (file.getRole() == PaperFileRole.COVER_LETTER ||
          file.getRole() == PaperFileRole.REVIEW_ONLY) &&
        file.getVisibility() != PaperFileVisibility.PRIVATE
      ) {
        add(
          issues,
          "file-upload",
          "files." + file.getId() + ".visibility",
          "PRIVATE_FILE_ROLE",
          "Cover Letter and Review Only files must remain private."
        );
      }
      if (
        file.getRole() == PaperFileRole.SUPPORTING_INFORMATION &&
        file.getVisibility() == PaperFileVisibility.PUBLIC &&
        clean(file.getDescription()) == null
      ) {
        add(
          issues,
          "file-upload",
          "files." + file.getId() + ".description",
          "PUBLIC_SI_DESCRIPTION_REQUIRED",
          "Describe the contents of each public Supporting Information file."
        );
      }
    }
  }

  private void requireExactlyOneRole(
    List<PaperSubmissionFile> files,
    PaperFileRole role,
    String label,
    List<PaperSubmissionIssueDto> issues
  ) {
    long count = files.stream().filter(file -> file.getRole() == role).count();
    if (count != 1) {
      add(
        issues,
        "file-upload",
        "files",
        "REQUIRED_FILE_ROLE",
        "Upload exactly one " + label + "."
      );
    }
  }

  private void validateMetadata(
    PaperSubmitRequest form,
    List<PaperSubmissionIssueDto> issues
  ) {
    requireText(issues, "manuscript-information", "title", form.getTitle(), "Enter the manuscript title.");
    requireText(
      issues,
      "manuscript-information",
      "abstractText",
      form.getAbstractText(),
      "Enter the manuscript abstract."
    );
    requireText(
      issues,
      "manuscript-information",
      "subjectArea",
      form.getSubjectArea(),
      "Select a section or subject area."
    );
    if (
      form.getKeywords() == null ||
      form.getKeywords().stream().map(PaperSubmissionValidator::clean).noneMatch(Objects::nonNull)
    ) {
      add(
        issues,
        "manuscript-information",
        "keywords",
        "KEYWORD_REQUIRED",
        "Add at least one keyword."
      );
    }
  }

  private void validateAuthors(
    List<PaperAuthorRequest> authors,
    List<PaperSubmissionIssueDto> issues
  ) {
    if (authors == null || authors.isEmpty()) {
      add(
        issues,
        "author-information",
        "authors",
        "AUTHOR_REQUIRED",
        "Add at least one author."
      );
      return;
    }

    long correspondingCount = authors
      .stream()
      .filter(Objects::nonNull)
      .filter(author -> Boolean.TRUE.equals(author.getCorrespondingAuthor()))
      .count();
    if (correspondingCount != 1) {
      add(
        issues,
        "author-information",
        "authors",
        "EXACTLY_ONE_CORRESPONDING_AUTHOR",
        "Select exactly one corresponding author."
      );
    }

    for (int index = 0; index < authors.size(); index++) {
      PaperAuthorRequest author = authors.get(index);
      String prefix = "authors[" + index + "]";
      if (author == null) {
        add(issues, "author-information", prefix, "INVALID_AUTHOR", "Complete this author record.");
        continue;
      }
      requireText(issues, "author-information", prefix + ".email", author.getEmail(), "Enter the author's email.");
      requireText(
        issues,
        "author-information",
        prefix + ".givenName",
        author.getGivenName(),
        "Enter the author's given name."
      );
      requireText(
        issues,
        "author-information",
        prefix + ".familyName",
        author.getFamilyName(),
        "Enter the author's family name."
      );
      requireText(
        issues,
        "author-information",
        prefix + ".authorRole",
        author.getAuthorRole(),
        "Select the author role."
      );
      validateAffiliations(author.getAffiliations(), prefix, issues);
    }
    validateCoFirstAuthors(authors, issues);
  }

  private void validateAffiliations(
    List<PaperAffiliationRequest> affiliations,
    String authorPrefix,
    List<PaperSubmissionIssueDto> issues
  ) {
    if (affiliations == null || affiliations.isEmpty()) {
      add(
        issues,
        "author-information",
        authorPrefix + ".affiliations",
        "AFFILIATION_REQUIRED",
        "Add at least one affiliation for this author."
      );
      return;
    }
    long primaryCount = affiliations
      .stream()
      .filter(Objects::nonNull)
      .filter(item -> Boolean.TRUE.equals(item.getPrimaryAffiliation()))
      .count();
    if (primaryCount != 1) {
      add(
        issues,
        "author-information",
        authorPrefix + ".affiliations",
        "EXACTLY_ONE_PRIMARY_AFFILIATION",
        "Select exactly one primary affiliation for this author."
      );
    }
    for (int index = 0; index < affiliations.size(); index++) {
      PaperAffiliationRequest affiliation = affiliations.get(index);
      String prefix = authorPrefix + ".affiliations[" + index + "]";
      if (affiliation == null) {
        add(issues, "author-information", prefix, "INVALID_AFFILIATION", "Complete this affiliation.");
        continue;
      }
      requireText(
        issues,
        "author-information",
        prefix + ".organizationName",
        affiliation.getOrganizationName(),
        "Enter the organization."
      );
      requireText(
        issues,
        "author-information",
        prefix + ".country",
        affiliation.getCountry(),
        "Select the country or region."
      );
      requireText(
        issues,
        "author-information",
        prefix + ".city",
        affiliation.getCity(),
        "Enter the city."
      );
    }
  }

  private void validateCoFirstAuthors(
    List<PaperAuthorRequest> authors,
    List<PaperSubmissionIssueDto> issues
  ) {
    List<Integer> marked = new ArrayList<>();
    for (int index = 0; index < authors.size(); index++) {
      PaperAuthorRequest author = authors.get(index);
      if (author != null && Boolean.TRUE.equals(author.getEqualContribution())) {
        marked.add(index);
      }
    }
    if (marked.isEmpty()) {
      return;
    }
    boolean continuous = marked.size() >= 2;
    for (int index = 0; index < marked.size(); index++) {
      continuous = continuous && marked.get(index) == index;
    }
    if (!continuous) {
      add(
        issues,
        "author-information",
        "authors",
        "INVALID_CO_FIRST_ORDER",
        "Co-first authors must start with the first author and remain continuous."
      );
    }
  }

  private void validateFunding(
    PaperSubmitRequest form,
    List<PaperSubmissionIssueDto> issues
  ) {
    boolean noFunding = Boolean.TRUE.equals(form.getNoFundingReceived());
    List<PaperFundingRequest> funding = form.getFunding() != null ? form.getFunding() : List.of();
    boolean hasFunding = funding
      .stream()
      .filter(Objects::nonNull)
      .map(PaperFundingRequest::getFunderName)
      .map(PaperSubmissionValidator::clean)
      .anyMatch(Objects::nonNull);
    if (noFunding == hasFunding) {
      add(
        issues,
        "funding-information",
        "funding",
        "FUNDING_SELECTION_REQUIRED",
        "Add at least one funder or select No funding was received."
      );
    }
    for (int index = 0; index < funding.size(); index++) {
      PaperFundingRequest item = funding.get(index);
      if (item != null && clean(item.getFunderName()) == null) {
        add(
          issues,
          "funding-information",
          "funding[" + index + "].funderName",
          "FUNDER_NAME_REQUIRED",
          "Enter the funder name."
        );
      }
    }
  }

  private void validateDeclarations(
    PaperSubmitRequest form,
    PaperSubmissionSubmitRequest confirmations,
    List<PaperSubmissionIssueDto> issues
  ) {
    requireText(
      issues,
      "details-comments",
      "conflictOfInterest",
      form.getConflictOfInterest(),
      "Provide a conflict of interest statement."
    );
    requireText(
      issues,
      "details-comments",
      "dataAvailability",
      form.getDataAvailability(),
      "Provide a data availability statement."
    );
    requireText(
      issues,
      "details-comments",
      "ethicsStatement",
      form.getEthicsStatement(),
      "Provide an ethics statement or explain why it is not applicable."
    );
    requireText(
      issues,
      "details-comments",
      "preprintStatement",
      form.getPreprintStatement(),
      "Describe any preprint or previous public posting, or state None."
    );
    requireText(
      issues,
      "details-comments",
      "aiUseDisclosure",
      form.getAiUseDisclosure(),
      "Disclose AI tool use, or state that no AI tools were used."
    );
    requireTrue(issues, "allAuthorsConsent", form.getAllAuthorsConsent(), "Confirm that all authors agreed to submission.");
    requireTrue(issues, "originalityConfirmed", form.getOriginalityConfirmed(), "Confirm originality.");
    requireTrue(issues, "rightsConfirmed", form.getRightsConfirmed(), "Confirm submission rights.");

    if (confirmations == null) {
      return;
    }
    requireTrue(
      issues,
      "correspondingAuthorContactConfirmed",
      form.getCorrespondingAuthorContactConfirmed(),
      "Confirm that the corresponding author's email may be shown publicly."
    );
    requireTrue(
      issues,
      "metadataMatchesManuscript",
      confirmations.getMetadataMatchesManuscript(),
      "Confirm that the metadata matches the manuscript."
    );
    requireTrue(
      issues,
      "correspondingAuthorInformationConfirmed",
      confirmations.getCorrespondingAuthorInformationConfirmed(),
      "Confirm the corresponding author information."
    );
    requireTrue(
      issues,
      "publicDisplayConfirmed",
      confirmations.getPublicDisplayConfirmed(),
      "Confirm the public display of approved files and declarations."
    );
    if (clean(confirmations.getIdempotencyKey()) == null) {
      add(
        issues,
        "details-comments",
        "idempotencyKey",
        "IDEMPOTENCY_KEY_REQUIRED",
        "A submission idempotency key is required."
      );
    }
  }

  private void requireTrue(
    List<PaperSubmissionIssueDto> issues,
    String field,
    Boolean value,
    String message
  ) {
    if (!Boolean.TRUE.equals(value)) {
      add(issues, "details-comments", field, "CONFIRMATION_REQUIRED", message);
    }
  }

  private void requireText(
    List<PaperSubmissionIssueDto> issues,
    String section,
    String field,
    String value,
    String message
  ) {
    if (clean(value) == null) {
      add(issues, section, field, "REQUIRED", message);
    }
  }

  private void add(
    List<PaperSubmissionIssueDto> issues,
    String section,
    String field,
    String code,
    String message
  ) {
    issues.add(new PaperSubmissionIssueDto(section, field, code, message));
  }

  private static String clean(String value) {
    if (value == null || value.isBlank()) {
      return null;
    }
    return value.trim();
  }

  private static String extension(String fileName) {
    String value = clean(fileName);
    if (value == null) {
      return "";
    }
    int dot = value.lastIndexOf('.');
    return dot >= 0 ? value.substring(dot + 1).toLowerCase(Locale.ROOT) : "";
  }
}
