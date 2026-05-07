# Paper MVP Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first backend slice of the paper platform: paper metadata entities, submission API, mock AI screening, and public paper feed/detail APIs.

**Architecture:** Keep OpenIsle's `Post` as the content and interaction anchor, then add a separate paper business layer. A paper submission creates a normal `Post` for full text, then creates `PaperProfile` and `PaperAuthor` records linked to that post. AI screening is mocked in this phase so the workflow can run before the algorithm team provides an API.

**Tech Stack:** Spring Boot 3.1.1, Java 17, Spring Data JPA, MySQL, SpringDoc OpenAPI, existing OpenIsle `PostService`, Nuxt/Vue frontend later.

---

## File Structure

Create backend model files:

- `backend/src/main/java/com/openisle/model/PaperPublicationStatus.java`
- `backend/src/main/java/com/openisle/model/PaperScreeningStatus.java`
- `backend/src/main/java/com/openisle/model/PaperProfile.java`
- `backend/src/main/java/com/openisle/model/PaperAuthor.java`
- `backend/src/main/java/com/openisle/model/Institution.java`
- `backend/src/main/java/com/openisle/model/AiScreeningResult.java`

Create backend repository files:

- `backend/src/main/java/com/openisle/repository/PaperProfileRepository.java`
- `backend/src/main/java/com/openisle/repository/PaperAuthorRepository.java`
- `backend/src/main/java/com/openisle/repository/InstitutionRepository.java`
- `backend/src/main/java/com/openisle/repository/AiScreeningResultRepository.java`

Create DTO files:

- `backend/src/main/java/com/openisle/dto/PaperAuthorRequest.java`
- `backend/src/main/java/com/openisle/dto/PaperSubmitRequest.java`
- `backend/src/main/java/com/openisle/dto/PaperSummaryDto.java`
- `backend/src/main/java/com/openisle/dto/PaperDetailDto.java`
- `backend/src/main/java/com/openisle/dto/AiScreeningDto.java`

Create service/controller files:

- `backend/src/main/java/com/openisle/service/PaperService.java`
- `backend/src/main/java/com/openisle/service/MockAiScreeningService.java`
- `backend/src/main/java/com/openisle/controller/PaperController.java`

Create tests:

- `backend/src/test/java/com/openisle/service/PaperServiceTest.java`

Modify only if needed:

- `backend/src/main/resources/application.properties`

---

## Developer Notes

### Why add PaperProfile instead of changing Post?

`Post` already has comments, tags, author, content, status, and existing frontend routes. Changing it into a paper table would make the community system fragile. `PaperProfile` keeps paper-specific fields separate while still reusing `Post.content` for the full paper text.

### Creation rule

One paper submission does this in a single transaction:

```text
Create Post
  -> Create or find Institution
  -> Create PaperProfile linked to Post
  -> Create PaperAuthor records linked to PaperProfile
  -> Create mock AiScreeningResult
  -> Mark PaperProfile as PUBLISHED if screening passed
```

### MVP simplification

Use mock AI screening now. The platform will define a stable interface so later the algorithm team can replace the implementation without changing frontend API.

---

## Task 1: Add Paper Domain Enums and Entities

**Files:**

- Create: `backend/src/main/java/com/openisle/model/PaperPublicationStatus.java`
- Create: `backend/src/main/java/com/openisle/model/PaperScreeningStatus.java`
- Create: `backend/src/main/java/com/openisle/model/Institution.java`
- Create: `backend/src/main/java/com/openisle/model/PaperProfile.java`
- Create: `backend/src/main/java/com/openisle/model/PaperAuthor.java`
- Create: `backend/src/main/java/com/openisle/model/AiScreeningResult.java`

- [ ] **Step 1: Create `PaperPublicationStatus`**

```java
package com.openisle.model;

public enum PaperPublicationStatus {
  DRAFT,
  SCREENING,
  PUBLISHED,
  NEEDS_REVISION,
  REJECTED,
  WITHDRAWN,
  RETRACTED
}
```

- [ ] **Step 2: Create `PaperScreeningStatus`**

```java
package com.openisle.model;

public enum PaperScreeningStatus {
  NOT_SCREENED,
  SCREENING,
  PASSED,
  NEEDS_REVISION,
  REJECTED_BY_POLICY,
  FAILED
}
```

- [ ] **Step 3: Create `Institution`**

```java
package com.openisle.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

@Entity
@Getter
@Setter
@NoArgsConstructor
@Table(
  name = "institutions",
  indexes = { @Index(name = "idx_institutions_name", columnList = "name") }
)
public class Institution {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(nullable = false, unique = true)
  private String name;

  @Column
  private String country;

  @Column
  private String type;

  @Column
  private String website;

  @Column(nullable = false)
  private boolean verified = false;

  @CreationTimestamp
  @Column(nullable = false, updatable = false)
  private LocalDateTime createdAt;

  @UpdateTimestamp
  @Column(nullable = false)
  private LocalDateTime updatedAt;
}
```

- [ ] **Step 4: Create `PaperProfile`**

```java
package com.openisle.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

@Entity
@Getter
@Setter
@NoArgsConstructor
@Table(
  name = "paper_profiles",
  indexes = {
    @Index(name = "idx_paper_profiles_status", columnList = "publicationStatus"),
    @Index(name = "idx_paper_profiles_subject", columnList = "subjectArea"),
    @Index(name = "idx_paper_profiles_published_at", columnList = "publishedAt")
  }
)
public class PaperProfile {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @OneToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "post_id", nullable = false, unique = true)
  private Post post;

  @Column(nullable = false)
  private String title;

  @Column(nullable = false, columnDefinition = "TEXT")
  private String abstractText;

  @Column(columnDefinition = "TEXT")
  private String keywords;

  @Column(nullable = false)
  private String subjectArea;

  @Column
  private String paperType;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  private PaperPublicationStatus publicationStatus = PaperPublicationStatus.DRAFT;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  private PaperScreeningStatus screeningStatus = PaperScreeningStatus.NOT_SCREENED;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "primary_institution_id")
  private Institution primaryInstitution;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "created_by")
  private User createdBy;

  @Column
  private LocalDateTime publishedAt;

  @CreationTimestamp
  @Column(nullable = false, updatable = false)
  private LocalDateTime createdAt;

  @UpdateTimestamp
  @Column(nullable = false)
  private LocalDateTime updatedAt;
}
```

- [ ] **Step 5: Create `PaperAuthor`**

```java
package com.openisle.model;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Getter
@Setter
@NoArgsConstructor
@Table(
  name = "paper_authors",
  indexes = {
    @Index(name = "idx_paper_authors_paper", columnList = "paper_id"),
    @Index(name = "idx_paper_authors_name", columnList = "displayName")
  }
)
public class PaperAuthor {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "paper_id", nullable = false)
  private PaperProfile paper;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "user_id")
  private User user;

  @Column(nullable = false)
  private String displayName;

  @Column
  private String email;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "institution_id")
  private Institution institution;

  @Column(nullable = false)
  private int authorOrder;

  @Column(nullable = false)
  private boolean correspondingAuthor = false;
}
```

- [ ] **Step 6: Create `AiScreeningResult`**

```java
package com.openisle.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;

@Entity
@Getter
@Setter
@NoArgsConstructor
@Table(name = "ai_screening_results")
public class AiScreeningResult {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @ManyToOne(optional = false, fetch = FetchType.LAZY)
  @JoinColumn(name = "paper_id", nullable = false)
  private PaperProfile paper;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  private PaperScreeningStatus status;

  @Column(nullable = false)
  private String riskLevel;

  @Column
  private String detectedSubjectArea;

  @Column
  private String detectedPaperType;

  @Column(columnDefinition = "TEXT")
  private String summary;

  @Column(columnDefinition = "TEXT")
  private String issuesJson;

  @Column(columnDefinition = "TEXT")
  private String rawResponseJson;

  @CreationTimestamp
  @Column(nullable = false, updatable = false)
  private LocalDateTime screenedAt;
}
```

- [ ] **Step 7: Compile check**

Run:

```powershell
docker compose -f docker/docker-compose.yaml --env-file .env exec springboot mvn -q -DskipTests compile
```

Expected: compile succeeds or reports missing repositories from later tasks. If missing repositories only, continue to Task 2.

---

## Task 2: Add Repositories

**Files:**

- Create: `backend/src/main/java/com/openisle/repository/PaperProfileRepository.java`
- Create: `backend/src/main/java/com/openisle/repository/PaperAuthorRepository.java`
- Create: `backend/src/main/java/com/openisle/repository/InstitutionRepository.java`
- Create: `backend/src/main/java/com/openisle/repository/AiScreeningResultRepository.java`

- [ ] **Step 1: Create `PaperProfileRepository`**

```java
package com.openisle.repository;

import com.openisle.model.PaperProfile;
import com.openisle.model.PaperPublicationStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaperProfileRepository extends JpaRepository<PaperProfile, Long> {
  Optional<PaperProfile> findByPostId(Long postId);

  List<PaperProfile> findByPublicationStatusOrderByPublishedAtDesc(
    PaperPublicationStatus status,
    Pageable pageable
  );
}
```

- [ ] **Step 2: Create `PaperAuthorRepository`**

```java
package com.openisle.repository;

import com.openisle.model.PaperAuthor;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaperAuthorRepository extends JpaRepository<PaperAuthor, Long> {
  List<PaperAuthor> findByPaperIdOrderByAuthorOrderAsc(Long paperId);
}
```

- [ ] **Step 3: Create `InstitutionRepository`**

```java
package com.openisle.repository;

import com.openisle.model.Institution;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InstitutionRepository extends JpaRepository<Institution, Long> {
  Optional<Institution> findByNameIgnoreCase(String name);
}
```

- [ ] **Step 4: Create `AiScreeningResultRepository`**

```java
package com.openisle.repository;

import com.openisle.model.AiScreeningResult;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AiScreeningResultRepository extends JpaRepository<AiScreeningResult, Long> {
  Optional<AiScreeningResult> findFirstByPaperIdOrderByScreenedAtDesc(Long paperId);
}
```

---

## Task 3: Add Paper DTOs

**Files:**

- Create: `backend/src/main/java/com/openisle/dto/PaperAuthorRequest.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperSubmitRequest.java`
- Create: `backend/src/main/java/com/openisle/dto/AiScreeningDto.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperSummaryDto.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperDetailDto.java`

- [ ] **Step 1: Create `PaperAuthorRequest`**

```java
package com.openisle.dto;

import lombok.Data;

@Data
public class PaperAuthorRequest {
  private String displayName;
  private String email;
  private String institutionName;
  private Boolean correspondingAuthor;
}
```

- [ ] **Step 2: Create `PaperSubmitRequest`**

```java
package com.openisle.dto;

import java.util.List;
import lombok.Data;

@Data
public class PaperSubmitRequest {
  private Long categoryId;
  private List<Long> tagIds;
  private String title;
  private String abstractText;
  private String keywords;
  private String subjectArea;
  private String paperType;
  private String content;
  private String primaryInstitutionName;
  private List<PaperAuthorRequest> authors;
}
```

- [ ] **Step 3: Create `AiScreeningDto`**

```java
package com.openisle.dto;

import com.openisle.model.PaperScreeningStatus;
import java.time.LocalDateTime;
import lombok.Data;

@Data
public class AiScreeningDto {
  private PaperScreeningStatus status;
  private String riskLevel;
  private String detectedSubjectArea;
  private String detectedPaperType;
  private String summary;
  private String issuesJson;
  private LocalDateTime screenedAt;
}
```

- [ ] **Step 4: Create `PaperSummaryDto`**

```java
package com.openisle.dto;

import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperScreeningStatus;
import java.time.LocalDateTime;
import java.util.List;
import lombok.Data;

@Data
public class PaperSummaryDto {
  private Long id;
  private Long postId;
  private String title;
  private String abstractText;
  private String subjectArea;
  private String paperType;
  private PaperPublicationStatus publicationStatus;
  private PaperScreeningStatus screeningStatus;
  private String primaryInstitutionName;
  private List<String> authors;
  private LocalDateTime publishedAt;
}
```

- [ ] **Step 5: Create `PaperDetailDto`**

```java
package com.openisle.dto;

import java.util.List;
import lombok.Data;

@Data
public class PaperDetailDto extends PaperSummaryDto {
  private String keywords;
  private String content;
  private List<String> authorInstitutions;
  private AiScreeningDto screening;
}
```

---

## Task 4: Add Mock AI Screening Service

**Files:**

- Create: `backend/src/main/java/com/openisle/service/MockAiScreeningService.java`

- [ ] **Step 1: Create service**

```java
package com.openisle.service;

import com.openisle.model.AiScreeningResult;
import com.openisle.model.PaperProfile;
import com.openisle.model.PaperScreeningStatus;
import org.springframework.stereotype.Service;

@Service
public class MockAiScreeningService {

  public AiScreeningResult screen(PaperProfile paper) {
    AiScreeningResult result = new AiScreeningResult();
    result.setPaper(paper);
    result.setStatus(PaperScreeningStatus.PASSED);
    result.setRiskLevel("LOW");
    result.setDetectedSubjectArea(paper.getSubjectArea());
    result.setDetectedPaperType(paper.getPaperType());
    result.setSummary("The submission passed the MVP screening checks.");
    result.setIssuesJson("[]");
    result.setRawResponseJson("{\"provider\":\"mock\",\"status\":\"PASSED\"}");
    return result;
  }
}
```

**Learning note:** This service is a seam. A seam is a place where we can later swap one implementation for another. Today it returns a fake pass result. Later it calls the algorithm team's API.

---

## Task 5: Add PaperService

**Files:**

- Create: `backend/src/main/java/com/openisle/service/PaperService.java`

- [ ] **Step 1: Create `PaperService`**

```java
package com.openisle.service;

import com.openisle.dto.*;
import com.openisle.exception.NotFoundException;
import com.openisle.model.*;
import com.openisle.repository.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class PaperService {

  private final PostService postService;
  private final PaperProfileRepository paperProfileRepository;
  private final PaperAuthorRepository paperAuthorRepository;
  private final InstitutionRepository institutionRepository;
  private final AiScreeningResultRepository aiScreeningResultRepository;
  private final MockAiScreeningService mockAiScreeningService;

  @Transactional
  public PaperDetailDto submitPaper(String username, PaperSubmitRequest request) {
    validateSubmitRequest(request);

    Post post = postService.createPost(
      username,
      request.getCategoryId(),
      request.getTitle(),
      request.getContent(),
      request.getTagIds(),
      PostType.NORMAL,
      PostVisibleScopeType.ALL,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null
    );

    Institution primaryInstitution = getOrCreateInstitution(request.getPrimaryInstitutionName());

    PaperProfile paper = new PaperProfile();
    paper.setPost(post);
    paper.setTitle(request.getTitle());
    paper.setAbstractText(request.getAbstractText());
    paper.setKeywords(request.getKeywords());
    paper.setSubjectArea(request.getSubjectArea());
    paper.setPaperType(request.getPaperType());
    paper.setPrimaryInstitution(primaryInstitution);
    paper.setCreatedBy(post.getAuthor());
    paper.setPublicationStatus(PaperPublicationStatus.SCREENING);
    paper.setScreeningStatus(PaperScreeningStatus.SCREENING);
    paper = paperProfileRepository.save(paper);

    saveAuthors(paper, request);

    AiScreeningResult screening = mockAiScreeningService.screen(paper);
    screening = aiScreeningResultRepository.save(screening);

    if (screening.getStatus() == PaperScreeningStatus.PASSED) {
      paper.setScreeningStatus(PaperScreeningStatus.PASSED);
      paper.setPublicationStatus(PaperPublicationStatus.PUBLISHED);
      paper.setPublishedAt(LocalDateTime.now());
      paper = paperProfileRepository.save(paper);
    }

    return toDetailDto(paper, screening);
  }

  public List<PaperSummaryDto> listPublishedPapers(int page, int pageSize) {
    return paperProfileRepository
      .findByPublicationStatusOrderByPublishedAtDesc(
        PaperPublicationStatus.PUBLISHED,
        PageRequest.of(Math.max(page, 0), Math.max(pageSize, 1))
      )
      .stream()
      .map(this::toSummaryDto)
      .toList();
  }

  public PaperDetailDto getPaper(Long paperId) {
    PaperProfile paper = paperProfileRepository
      .findById(paperId)
      .orElseThrow(() -> new NotFoundException("Paper not found"));
    AiScreeningResult screening = aiScreeningResultRepository
      .findFirstByPaperIdOrderByScreenedAtDesc(paperId)
      .orElse(null);
    return toDetailDto(paper, screening);
  }

  private void validateSubmitRequest(PaperSubmitRequest request) {
    if (request.getTitle() == null || request.getTitle().isBlank()) {
      throw new IllegalArgumentException("Title is required");
    }
    if (request.getAbstractText() == null || request.getAbstractText().isBlank()) {
      throw new IllegalArgumentException("Abstract is required");
    }
    if (request.getContent() == null || request.getContent().isBlank()) {
      throw new IllegalArgumentException("Full text is required");
    }
    if (request.getSubjectArea() == null || request.getSubjectArea().isBlank()) {
      throw new IllegalArgumentException("Subject area is required");
    }
    if (request.getAuthors() == null || request.getAuthors().isEmpty()) {
      throw new IllegalArgumentException("At least one author is required");
    }
  }

  private Institution getOrCreateInstitution(String institutionName) {
    if (institutionName == null || institutionName.isBlank()) {
      return null;
    }
    String normalizedName = institutionName.trim();
    return institutionRepository
      .findByNameIgnoreCase(normalizedName)
      .orElseGet(() -> {
        Institution institution = new Institution();
        institution.setName(normalizedName);
        institution.setType("UNSPECIFIED");
        return institutionRepository.save(institution);
      });
  }

  private void saveAuthors(PaperProfile paper, PaperSubmitRequest request) {
    List<PaperAuthor> authors = new ArrayList<>();
    for (int i = 0; i < request.getAuthors().size(); i++) {
      PaperAuthorRequest authorRequest = request.getAuthors().get(i);
      PaperAuthor author = new PaperAuthor();
      author.setPaper(paper);
      author.setDisplayName(authorRequest.getDisplayName());
      author.setEmail(authorRequest.getEmail());
      author.setAuthorOrder(i + 1);
      author.setCorrespondingAuthor(Boolean.TRUE.equals(authorRequest.getCorrespondingAuthor()));
      author.setInstitution(getOrCreateInstitution(authorRequest.getInstitutionName()));
      authors.add(author);
    }
    paperAuthorRepository.saveAll(authors);
  }

  private PaperSummaryDto toSummaryDto(PaperProfile paper) {
    PaperSummaryDto dto = new PaperSummaryDto();
    dto.setId(paper.getId());
    dto.setPostId(paper.getPost().getId());
    dto.setTitle(paper.getTitle());
    dto.setAbstractText(paper.getAbstractText());
    dto.setSubjectArea(paper.getSubjectArea());
    dto.setPaperType(paper.getPaperType());
    dto.setPublicationStatus(paper.getPublicationStatus());
    dto.setScreeningStatus(paper.getScreeningStatus());
    dto.setPublishedAt(paper.getPublishedAt());
    dto.setPrimaryInstitutionName(
      paper.getPrimaryInstitution() != null ? paper.getPrimaryInstitution().getName() : null
    );
    dto.setAuthors(
      paperAuthorRepository
        .findByPaperIdOrderByAuthorOrderAsc(paper.getId())
        .stream()
        .map(PaperAuthor::getDisplayName)
        .filter(Objects::nonNull)
        .toList()
    );
    return dto;
  }

  private PaperDetailDto toDetailDto(PaperProfile paper, AiScreeningResult screening) {
    PaperDetailDto dto = new PaperDetailDto();
    PaperSummaryDto summary = toSummaryDto(paper);
    dto.setId(summary.getId());
    dto.setPostId(summary.getPostId());
    dto.setTitle(summary.getTitle());
    dto.setAbstractText(summary.getAbstractText());
    dto.setSubjectArea(summary.getSubjectArea());
    dto.setPaperType(summary.getPaperType());
    dto.setPublicationStatus(summary.getPublicationStatus());
    dto.setScreeningStatus(summary.getScreeningStatus());
    dto.setPrimaryInstitutionName(summary.getPrimaryInstitutionName());
    dto.setAuthors(summary.getAuthors());
    dto.setPublishedAt(summary.getPublishedAt());
    dto.setKeywords(paper.getKeywords());
    dto.setContent(paper.getPost().getContent());
    dto.setAuthorInstitutions(
      paperAuthorRepository
        .findByPaperIdOrderByAuthorOrderAsc(paper.getId())
        .stream()
        .map(author -> author.getInstitution() != null ? author.getInstitution().getName() : null)
        .filter(Objects::nonNull)
        .toList()
    );
    dto.setScreening(toScreeningDto(screening));
    return dto;
  }

  private AiScreeningDto toScreeningDto(AiScreeningResult screening) {
    if (screening == null) {
      return null;
    }
    AiScreeningDto dto = new AiScreeningDto();
    dto.setStatus(screening.getStatus());
    dto.setRiskLevel(screening.getRiskLevel());
    dto.setDetectedSubjectArea(screening.getDetectedSubjectArea());
    dto.setDetectedPaperType(screening.getDetectedPaperType());
    dto.setSummary(screening.getSummary());
    dto.setIssuesJson(screening.getIssuesJson());
    dto.setScreenedAt(screening.getScreenedAt());
    return dto;
  }
}
```

---

## Task 6: Add PaperController

**Files:**

- Create: `backend/src/main/java/com/openisle/controller/PaperController.java`

- [ ] **Step 1: Create controller**

```java
package com.openisle.controller;

import com.openisle.dto.PaperDetailDto;
import com.openisle.dto.PaperSubmitRequest;
import com.openisle.dto.PaperSummaryDto;
import com.openisle.service.PaperService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/papers")
@RequiredArgsConstructor
@Tag(name = "Papers", description = "Paper submission and publication APIs")
public class PaperController {

  private final PaperService paperService;

  @PostMapping
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Submit paper", description = "Create a paper and run MVP AI screening.")
  public ResponseEntity<PaperDetailDto> submitPaper(
    @RequestBody PaperSubmitRequest request,
    Authentication authentication
  ) {
    return ResponseEntity.ok(paperService.submitPaper(authentication.getName(), request));
  }

  @GetMapping
  @Operation(summary = "List published papers", description = "Return public paper feed.")
  public List<PaperSummaryDto> listPapers(
    @RequestParam(value = "page", defaultValue = "0") int page,
    @RequestParam(value = "pageSize", defaultValue = "20") int pageSize
  ) {
    return paperService.listPublishedPapers(page, pageSize);
  }

  @GetMapping("/{paperId}")
  @Operation(summary = "Get paper detail", description = "Return paper metadata and full text.")
  public PaperDetailDto getPaper(@PathVariable Long paperId) {
    return paperService.getPaper(paperId);
  }
}
```

---

## Task 7: Add First Service Test

**Files:**

- Create: `backend/src/test/java/com/openisle/service/PaperServiceTest.java`

- [ ] **Step 1: Create integration-style service test**

```java
package com.openisle.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.openisle.dto.PaperAuthorRequest;
import com.openisle.dto.PaperDetailDto;
import com.openisle.dto.PaperSubmitRequest;
import com.openisle.model.PaperPublicationStatus;
import com.openisle.model.PaperScreeningStatus;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class PaperServiceTest {

  @Autowired
  private PaperService paperService;

  @Test
  void submitPaperCreatesPublishedPaperAfterMockScreening() {
    PaperAuthorRequest author = new PaperAuthorRequest();
    author.setDisplayName("Alice Researcher");
    author.setInstitutionName("Example University");
    author.setCorrespondingAuthor(true);

    PaperSubmitRequest request = new PaperSubmitRequest();
    request.setCategoryId(1L);
    request.setTagIds(List.of(1L));
    request.setTitle("A Test Paper for MVP Workflow");
    request.setAbstractText("This abstract exists to test paper submission.");
    request.setKeywords("paper,mvp,test");
    request.setSubjectArea("Information Systems");
    request.setPaperType("Research Article");
    request.setContent("Full paper text for the MVP workflow test.");
    request.setPrimaryInstitutionName("Example University");
    request.setAuthors(List.of(author));

    PaperDetailDto result = paperService.submitPaper("admin", request);

    assertThat(result.getId()).isNotNull();
    assertThat(result.getPostId()).isNotNull();
    assertThat(result.getPublicationStatus()).isEqualTo(PaperPublicationStatus.PUBLISHED);
    assertThat(result.getScreeningStatus()).isEqualTo(PaperScreeningStatus.PASSED);
    assertThat(result.getScreening().getRiskLevel()).isEqualTo("LOW");
  }
}
```

- [ ] **Step 2: Run test**

Run:

```powershell
docker compose -f docker/docker-compose.yaml --env-file .env exec springboot mvn -Dtest=PaperServiceTest test
```

Expected:

```text
BUILD SUCCESS
```

If test data for category/tag is missing in test profile, inspect `backend/src/test/resources/application.properties` and seed setup, then either add test fixtures or convert the test to mock `PostService`.

---

## Task 8: Manual API Smoke Test

**Files:** no code changes.

- [ ] **Step 1: Get JWT token by logging in through frontend**

Use the browser at:

```text
http://localhost:3000/login
```

Login:

```text
admin / 123456
```

Get token from browser devtools local storage or existing auth storage.

- [ ] **Step 2: Call paper submission API**

Run with token:

```powershell
$token = "PASTE_TOKEN_HERE"
$body = @{
  categoryId = 1
  tagIds = @(1)
  title = "Platform Evaluation for Open Research"
  abstractText = "This paper demonstrates the MVP paper submission workflow."
  keywords = "open research,evaluation,platform"
  subjectArea = "Information Systems"
  paperType = "Research Article"
  content = "This is the full paper text stored in Post.content."
  primaryInstitutionName = "Example University"
  authors = @(@{
    displayName = "Alice Researcher"
    email = "alice@example.edu"
    institutionName = "Example University"
    correspondingAuthor = $true
  })
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://localhost:8080/api/papers" -Method Post -Headers @{Authorization="Bearer $token"} -ContentType "application/json" -Body $body
```

Expected:

```text
publicationStatus: PUBLISHED
screeningStatus: PASSED
```

- [ ] **Step 3: Check public feed**

Run:

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/api/papers?page=0&pageSize=10"
```

Expected: response includes the submitted paper.

---

## Learning Explanation for the User

本阶段开发的核心软件工程思路：

1. **不改核心，先加扩展层。** OpenIsle 的 `Post` 系统已经复杂，直接硬改风险大，所以我们新增 `PaperProfile`。
2. **用关联而不是复制。** 论文全文放在 `Post.content`，论文元数据放在 `PaperProfile`，两者通过 `post_id` 关联。
3. **Service 层负责业务事务。** `PaperService.submitPaper()` 一次完成创建 Post、创建 PaperProfile、保存作者、AI mock screening、发布。
4. **Controller 只做入口。** `PaperController` 不写复杂逻辑，只接收请求并调用 service。
5. **Mock 外部系统。** 算法团队 API 还没有时，用 `MockAiScreeningService` 先跑通流程。

---

## Verification Checklist

- [ ] Backend compiles.
- [ ] `PaperServiceTest` passes or test fixture issue is documented.
- [ ] `POST /api/papers` creates a paper.
- [ ] Created paper has linked `Post`.
- [ ] Created paper has at least one `PaperAuthor`.
- [ ] Created paper has an `AiScreeningResult`.
- [ ] Mock screening publishes the paper.
- [ ] `GET /api/papers` returns published papers.
- [ ] `GET /api/papers/{paperId}` returns metadata and full text.
