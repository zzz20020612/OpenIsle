package com.openisle.controller;

import com.openisle.dto.*;
import com.openisle.exception.NotFoundException;
import com.openisle.mapper.TagMapper;
import com.openisle.mapper.UserMapper;
import com.openisle.model.User;
import com.openisle.service.*;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import java.io.IOException;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

  private final UserService userService;
  private final ImageUploader imageUploader;
  private final PostService postService;
  private final CommentService commentService;
  private final ReactionService reactionService;
  private final TagService tagService;
  private final SubscriptionService subscriptionService;
  private final LevelService levelService;
  private final PostReadService postReadService;
  private final JwtService jwtService;
  private final UserMapper userMapper;
  private final TagMapper tagMapper;

  @Value("${app.upload.check-type:true}")
  private boolean checkImageType;

  @Value("${app.upload.max-size:5242880}")
  private long maxUploadSize;

  @Value("${app.user.posts-limit:10}")
  private int defaultPostsLimit;

  @Value("${app.user.replies-limit:50}")
  private int defaultRepliesLimit;

  @Value("${app.user.tags-limit:50}")
  private int defaultTagsLimit;

  @Value("${app.user.read-posts-limit:50}")
  private int defaultReadPostsLimit;

  @GetMapping("/me")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Current user", description = "Get current authenticated user information")
  @ApiResponse(
    responseCode = "200",
    description = "User detail",
    content = @Content(schema = @Schema(implementation = UserDto.class))
  )
  public ResponseEntity<UserDto> me(Authentication auth) {
    User user = userService.findByUsername(auth.getName()).orElseThrow();
    return ResponseEntity.ok(userMapper.toDto(user, auth));
  }

  @PostMapping("/me/avatar")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Upload avatar", description = "Upload avatar for current user")
  @ApiResponse(
    responseCode = "200",
    description = "Upload result",
    content = @Content(schema = @Schema(implementation = Map.class))
  )
  public ResponseEntity<?> uploadAvatar(
    @RequestParam("file") MultipartFile file,
    Authentication auth
  ) {
    if (
      checkImageType &&
      (file.getContentType() == null || !file.getContentType().startsWith("image/"))
    ) {
      return ResponseEntity.badRequest().body(Map.of("error", "File is not an image"));
    }
    if (file.getSize() > maxUploadSize) {
      return ResponseEntity.badRequest().body(Map.of("error", "File too large"));
    }
    String url = null;
    try {
      url = imageUploader.upload(file.getBytes(), file.getOriginalFilename()).join();
    } catch (IOException e) {
      return ResponseEntity.internalServerError().body(Map.of("url", url));
    }
    userService.updateAvatar(auth.getName(), url);
    return ResponseEntity.ok(Map.of("url", url));
  }

  @PutMapping("/me")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Update profile", description = "Update current user's profile")
  @ApiResponse(
    responseCode = "200",
    description = "Updated profile",
    content = @Content(schema = @Schema(implementation = Map.class))
  )
  public ResponseEntity<?> updateProfile(@RequestBody UpdateProfileDto dto, Authentication auth) {
    User user = userService.updateProfile(auth.getName(), dto.getUsername(), dto.getIntroduction());
    return ResponseEntity.ok(
      Map.of(
        "token",
        jwtService.generateToken(user.getUsername()),
        "user",
        userMapper.toDto(user, auth)
      )
    );
  }

  // 这个方法似乎没有使用？
  @PostMapping("/me/signin")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "Daily sign in", description = "Sign in to receive rewards")
  @ApiResponse(
    responseCode = "200",
    description = "Sign in reward",
    content = @Content(schema = @Schema(implementation = Map.class))
  )
  public Map<String, Integer> signIn(Authentication auth) {
    int reward = levelService.awardForSignin(auth.getName());
    return Map.of("reward", reward);
  }

  @GetMapping("/{identifier}")
  @Operation(summary = "Get user", description = "Get user by identifier")
  @ApiResponse(
    responseCode = "200",
    description = "User detail",
    content = @Content(schema = @Schema(implementation = UserDto.class))
  )
  public ResponseEntity<UserDto> getUser(
    @PathVariable("identifier") String identifier,
    Authentication auth
  ) {
    User user = userService
      .findByIdentifier(identifier)
      .orElseThrow(() -> new NotFoundException("User not found"));
    return ResponseEntity.ok(userMapper.toDto(user, auth));
  }

  @GetMapping("/{identifier}/posts")
  @Operation(summary = "User posts", description = "Get recent posts by user")
  @ApiResponse(
    responseCode = "200",
    description = "User posts",
    content = @Content(array = @ArraySchema(schema = @Schema(implementation = PostMetaDto.class)))
  )
  public java.util.List<PostMetaDto> userPosts(
    @PathVariable("identifier") String identifier,
    @RequestParam(value = "limit", required = false) Integer limit
  ) {
    int l = limit != null ? limit : defaultPostsLimit;
    User user = userService.findByIdentifier(identifier).orElseThrow();
    return postService
      .getRecentPostsByUser(user.getUsername(), l)
      .stream()
      .filter(userMapper::isPublicProfileContent)
      .map(userMapper::toMetaDto)
      .collect(java.util.stream.Collectors.toList());
  }

  @GetMapping("/{identifier}/subscribed-posts")
  @Operation(summary = "Subscribed posts", description = "Get posts the user subscribed to")
  @ApiResponse(
    responseCode = "200",
    description = "Subscribed posts",
    content = @Content(array = @ArraySchema(schema = @Schema(implementation = PostMetaDto.class)))
  )
  public java.util.List<PostMetaDto> subscribedPosts(
    @PathVariable("identifier") String identifier,
    @RequestParam(value = "limit", required = false) Integer limit
  ) {
    int l = limit != null ? limit : defaultPostsLimit;
    User user = userService.findByIdentifier(identifier).orElseThrow();
    return subscriptionService
      .getSubscribedPosts(user.getUsername())
      .stream()
      .filter(userMapper::isPublicProfileContent)
      .limit(l)
      .map(userMapper::toMetaDto)
      .collect(java.util.stream.Collectors.toList());
  }

  @GetMapping("/{identifier}/replies")
  @Operation(summary = "User replies", description = "Get recent replies by user")
  @ApiResponse(
    responseCode = "200",
    description = "User replies",
    content = @Content(
      array = @ArraySchema(schema = @Schema(implementation = CommentInfoDto.class))
    )
  )
  public java.util.List<CommentInfoDto> userReplies(
    @PathVariable("identifier") String identifier,
    @RequestParam(value = "limit", required = false) Integer limit
  ) {
    int l = limit != null ? limit : defaultRepliesLimit;
    User user = userService.findByIdentifier(identifier).orElseThrow();
    return commentService
      .getRecentCommentsByUser(user.getUsername(), l)
      .stream()
      .filter(comment -> userMapper.isPublicProfileContent(comment.getPost()))
      .map(userMapper::toCommentInfoDto)
      .collect(java.util.stream.Collectors.toList());
  }

  @GetMapping("/{identifier}/read-posts")
  @SecurityRequirement(name = "JWT")
  @Operation(summary = "User read posts", description = "Get post read history (self only)")
  @ApiResponse(
    responseCode = "200",
    description = "Post read history",
    content = @Content(array = @ArraySchema(schema = @Schema(implementation = PostReadDto.class)))
  )
  public ResponseEntity<java.util.List<PostReadDto>> userReadPosts(
    @PathVariable("identifier") String identifier,
    @RequestParam(value = "limit", required = false) Integer limit,
    Authentication auth
  ) {
    User user = userService.findByIdentifier(identifier).orElseThrow();
    if (auth == null || !auth.getName().equals(user.getUsername())) {
      return ResponseEntity.status(403).body(java.util.List.of());
    }
    int l = limit != null ? limit : defaultReadPostsLimit;
    return ResponseEntity.ok(
      postReadService
        .getRecentReadsByUser(user.getUsername(), l)
        .stream()
        .filter(read -> userMapper.isPublicProfileContent(read.getPost()))
        .map(userMapper::toPostReadDto)
        .collect(java.util.stream.Collectors.toList())
    );
  }

  @GetMapping("/{identifier}/hot-posts")
  @Operation(summary = "User hot posts", description = "Get most reacted posts by user")
  @ApiResponse(
    responseCode = "200",
    description = "Hot posts",
    content = @Content(array = @ArraySchema(schema = @Schema(implementation = PostMetaDto.class)))
  )
  public java.util.List<PostMetaDto> hotPosts(
    @PathVariable("identifier") String identifier,
    @RequestParam(value = "limit", required = false) Integer limit
  ) {
    int l = limit != null ? limit : 10;
    User user = userService.findByIdentifier(identifier).orElseThrow();
    java.util.List<Long> ids = reactionService.topPostIds(user.getUsername(), l);
    return postService
      .getPostsByIds(ids)
      .stream()
      .filter(userMapper::isPublicProfileContent)
      .map(userMapper::toMetaDto)
      .collect(java.util.stream.Collectors.toList());
  }

  @GetMapping("/{identifier}/hot-replies")
  @Operation(summary = "User hot replies", description = "Get most reacted replies by user")
  @ApiResponse(
    responseCode = "200",
    description = "Hot replies",
    content = @Content(
      array = @ArraySchema(schema = @Schema(implementation = CommentInfoDto.class))
    )
  )
  public java.util.List<CommentInfoDto> hotReplies(
    @PathVariable("identifier") String identifier,
    @RequestParam(value = "limit", required = false) Integer limit
  ) {
    int l = limit != null ? limit : 10;
    User user = userService.findByIdentifier(identifier).orElseThrow();
    java.util.List<Long> ids = reactionService.topCommentIds(user.getUsername(), l);
    return commentService
      .getCommentsByIds(ids)
      .stream()
      .filter(comment -> userMapper.isPublicProfileContent(comment.getPost()))
      .map(userMapper::toCommentInfoDto)
      .collect(java.util.stream.Collectors.toList());
  }

  @GetMapping("/{identifier}/hot-tags")
  @Operation(summary = "User hot tags", description = "Get tags frequently used by user")
  @ApiResponse(
    responseCode = "200",
    description = "Hot tags",
    content = @Content(array = @ArraySchema(schema = @Schema(implementation = TagDto.class)))
  )
  public java.util.List<TagDto> hotTags(
    @PathVariable("identifier") String identifier,
    @RequestParam(value = "limit", required = false) Integer limit
  ) {
    int l = limit != null ? limit : 10;
    User user = userService.findByIdentifier(identifier).orElseThrow();
    return tagService
      .getTagsByUser(user.getUsername())
      .stream()
      .map(t -> tagMapper.toDto(t, postService.countPostsByTag(t.getId())))
      .sorted((a, b) -> Long.compare(b.getCount(), a.getCount()))
      .limit(l)
      .collect(java.util.stream.Collectors.toList());
  }

  @GetMapping("/{identifier}/tags")
  @Operation(summary = "User tags", description = "Get recent tags used by user")
  @ApiResponse(
    responseCode = "200",
    description = "User tags",
    content = @Content(array = @ArraySchema(schema = @Schema(implementation = TagDto.class)))
  )
  public java.util.List<TagDto> userTags(
    @PathVariable("identifier") String identifier,
    @RequestParam(value = "limit", required = false) Integer limit
  ) {
    int l = limit != null ? limit : defaultTagsLimit;
    User user = userService.findByIdentifier(identifier).orElseThrow();
    return tagService
      .getRecentTagsByUser(user.getUsername(), l)
      .stream()
      .map(t -> tagMapper.toDto(t, postService.countPostsByTag(t.getId())))
      .collect(java.util.stream.Collectors.toList());
  }

  @GetMapping("/{identifier}/following")
  @Operation(summary = "Following users", description = "Get users that this user is following")
  @ApiResponse(
    responseCode = "200",
    description = "Following list",
    content = @Content(array = @ArraySchema(schema = @Schema(implementation = UserDto.class)))
  )
  public java.util.List<UserDto> following(@PathVariable("identifier") String identifier) {
    User user = userService.findByIdentifier(identifier).orElseThrow();
    return subscriptionService
      .getSubscribedUsers(user.getUsername())
      .stream()
      .map(userMapper::toDto)
      .collect(java.util.stream.Collectors.toList());
  }

  @GetMapping("/{identifier}/followers")
  @Operation(summary = "Followers", description = "Get followers of this user")
  @ApiResponse(
    responseCode = "200",
    description = "Followers list",
    content = @Content(array = @ArraySchema(schema = @Schema(implementation = UserDto.class)))
  )
  public java.util.List<UserDto> followers(@PathVariable("identifier") String identifier) {
    User user = userService.findByIdentifier(identifier).orElseThrow();
    return subscriptionService
      .getSubscribers(user.getUsername())
      .stream()
      .map(userMapper::toDto)
      .collect(java.util.stream.Collectors.toList());
  }

  @GetMapping("/admins")
  @Operation(summary = "Admin users", description = "List administrator users")
  @ApiResponse(
    responseCode = "200",
    description = "Admin users",
    content = @Content(array = @ArraySchema(schema = @Schema(implementation = UserDto.class)))
  )
  public java.util.List<UserDto> admins() {
    return userService
      .getAdmins()
      .stream()
      .map(userMapper::toDto)
      .collect(java.util.stream.Collectors.toList());
  }

  @GetMapping("/{identifier}/all")
  @Operation(summary = "User aggregate", description = "Get aggregate information for user")
  @ApiResponse(
    responseCode = "200",
    description = "User aggregate",
    content = @Content(schema = @Schema(implementation = UserAggregateDto.class))
  )
  public ResponseEntity<UserAggregateDto> userAggregate(
    @PathVariable("identifier") String identifier,
    @RequestParam(value = "postsLimit", required = false) Integer postsLimit,
    @RequestParam(value = "repliesLimit", required = false) Integer repliesLimit,
    Authentication auth
  ) {
    User user = userService.findByIdentifier(identifier).orElseThrow();
    int pLimit = postsLimit != null ? postsLimit : defaultPostsLimit;
    int rLimit = repliesLimit != null ? repliesLimit : defaultRepliesLimit;
    java.util.List<PostMetaDto> posts = postService
      .getRecentPostsByUser(user.getUsername(), pLimit)
      .stream()
      .filter(userMapper::isPublicProfileContent)
      .map(userMapper::toMetaDto)
      .collect(java.util.stream.Collectors.toList());
    java.util.List<CommentInfoDto> replies = commentService
      .getRecentCommentsByUser(user.getUsername(), rLimit)
      .stream()
      .filter(comment -> userMapper.isPublicProfileContent(comment.getPost()))
      .map(userMapper::toCommentInfoDto)
      .collect(java.util.stream.Collectors.toList());
    UserAggregateDto dto = new UserAggregateDto();
    dto.setUser(userMapper.toDto(user, auth));
    dto.setPosts(posts);
    dto.setReplies(replies);
    return ResponseEntity.ok(dto);
  }
}
