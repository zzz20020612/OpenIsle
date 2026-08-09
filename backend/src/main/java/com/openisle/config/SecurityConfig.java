package com.openisle.config;

import com.openisle.repository.UserRepository;
import com.openisle.service.JwtService;
import com.openisle.service.UserVisitService;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.LocalDate;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.authentication.builders.AuthenticationManagerBuilder;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.OncePerRequestFilter;

@Configuration
@RequiredArgsConstructor
public class SecurityConfig {

  private final JwtService jwtService;
  private final UserRepository userRepository;
  private final AccessDeniedHandler customAccessDeniedHandler;
  private final UserVisitService userVisitService;

  @Value("${app.website-url}")
  private String websiteUrl;

  private final RedisTemplate redisTemplate;

  @Bean
  public PasswordEncoder passwordEncoder() {
    return new BCryptPasswordEncoder();
  }

  @Bean
  public UserDetailsService userDetailsService() {
    return username ->
      userRepository
        .findByUsername(username)
        .<UserDetails>map(user ->
          org.springframework.security.core.userdetails.User.withUsername(user.getUsername())
            .password(user.getPassword())
            .authorities(user.getRole().name())
            .build()
        )
        .orElseThrow(() -> new UsernameNotFoundException("User not found"));
  }

  @Bean
  public AuthenticationManager authenticationManager(
    HttpSecurity http,
    PasswordEncoder passwordEncoder,
    UserDetailsService userDetailsService
  ) throws Exception {
    return http
      .getSharedObject(AuthenticationManagerBuilder.class)
      .userDetailsService(userDetailsService)
      .passwordEncoder(passwordEncoder)
      .and()
      .build();
  }

  @Bean
  public CorsConfigurationSource corsConfigurationSource() {
    CorsConfiguration cfg = new CorsConfiguration();
    cfg.setAllowedOrigins(
      List.of(
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
        "http://127.0.0.1:8082",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://localhost:8082",
        "http://localhost:3000",
        "http://frontend_dev:3000",
        "http://frontend_service:3000",
        "http://localhost:3001",
        "http://localhost",
        "http://30.211.97.238:3000",
        "http://30.211.97.238",
        "http://192.168.7.90",
        "http://192.168.7.90:3000",
        "https://petstore.swagger.io",
        // 允许自建OpenAPI地址
        "https://docs.open-isle.com",
        "https://www.docs.open-isle.com",
        websiteUrl,
        websiteUrl.replace("://www.", "://")
      )
    );
    cfg.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
    cfg.setAllowedHeaders(List.of("*"));
    cfg.setAllowCredentials(true);
    UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
    source.registerCorsConfiguration("/api/**", cfg);
    return source;
  }

  @Bean
  public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    http
      .csrf(csrf -> csrf.disable())
      .cors(Customizer.withDefaults())
      .headers(h -> h.frameOptions(f -> f.sameOrigin()))
      .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
      .exceptionHandling(eh -> eh.accessDeniedHandler(customAccessDeniedHandler))
      .authorizeHttpRequests(auth ->
        auth
          .requestMatchers(HttpMethod.OPTIONS, "/**")
          .permitAll()
          .requestMatchers("/api/ws/**", "/api/sockjs/**")
          .permitAll()
          .requestMatchers("/api/v3/api-docs/**")
          .permitAll()
          .requestMatchers(HttpMethod.POST, "/api/auth/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/posts/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/papers/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/literature/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/experts/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/comments/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/categories/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/tags/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/config/**")
          .permitAll()
          .requestMatchers(HttpMethod.POST, "/api/auth/google")
          .permitAll()
          .requestMatchers(HttpMethod.POST, "/api/auth/reason")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/search/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/users/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/medals/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/push/public-key")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/reaction-types")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/activities/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/sitemap.xml")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/channels")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/rss")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/online/**")
          .permitAll()
          .requestMatchers(HttpMethod.POST, "/api/online/**")
          .permitAll()
          .requestMatchers(HttpMethod.PUT, "/api/upload/local/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/upload/local/file/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/upload/local/download/**")
          .permitAll()
          .requestMatchers(HttpMethod.GET, "/api/point-goods")
          .permitAll()
          .requestMatchers(HttpMethod.POST, "/api/point-goods")
          .permitAll()
          .requestMatchers("/actuator/**")
          .permitAll()
          .requestMatchers(HttpMethod.POST, "/api/categories/**")
          .hasAuthority("ADMIN")
          .requestMatchers(HttpMethod.POST, "/api/tags/**")
          .authenticated()
          .requestMatchers(HttpMethod.DELETE, "/api/categories/**")
          .hasAuthority("ADMIN")
          .requestMatchers(HttpMethod.DELETE, "/api/tags/**")
          .hasAuthority("ADMIN")
          .requestMatchers(HttpMethod.GET, "/api/stats/**")
          .hasAuthority("ADMIN")
          .requestMatchers("/api/admin/**")
          .hasAuthority("ADMIN")
          .anyRequest()
          .authenticated()
      )
      .addFilterBefore(jwtAuthenticationFilter(), UsernamePasswordAuthenticationFilter.class)
      .addFilterAfter(userVisitFilter(), UsernamePasswordAuthenticationFilter.class);
    return http.build();
  }

  @Bean
  public OncePerRequestFilter jwtAuthenticationFilter() {
    return new OncePerRequestFilter() {
      @Override
      protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
      ) throws ServletException, IOException {
        // 让预检请求直接通过
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
          filterChain.doFilter(request, response);
          return;
        }
        String authHeader = request.getHeader("Authorization");
        String uri = request.getRequestURI();
        boolean localUpload =
          uri.startsWith("/api/upload/local/") &&
          ("PUT".equalsIgnoreCase(request.getMethod()) || "GET".equalsIgnoreCase(request.getMethod()));

        boolean publicGet =
          "GET".equalsIgnoreCase(request.getMethod()) &&
          (uri.startsWith("/api/posts") ||
            uri.startsWith("/api/papers") ||
            uri.startsWith("/api/literature") ||
            uri.startsWith("/api/experts") ||
            uri.startsWith("/api/comments") ||
            uri.startsWith("/api/categories") ||
            uri.startsWith("/api/tags") ||
            uri.startsWith("/api/search") ||
            uri.startsWith("/api/users") ||
            uri.startsWith("/api/reaction-types") ||
            uri.startsWith("/api/config") ||
            uri.startsWith("/api/activities") ||
            uri.startsWith("/api/push/public-key") ||
            uri.startsWith("/api/point-goods") ||
            uri.startsWith("/api/channels") ||
            uri.startsWith("/api/sitemap.xml") ||
            uri.startsWith("/api/medals") ||
            uri.startsWith("/actuator") ||
            uri.startsWith("/api/rss"));

        if (authHeader != null && authHeader.startsWith("Bearer ")) {
          String token = authHeader.substring(7);
          try {
            String username = jwtService.validateAndGetSubject(token);
            UserDetails userDetails = userDetailsService().loadUserByUsername(username);
            UsernamePasswordAuthenticationToken authToken = new UsernamePasswordAuthenticationToken(
              userDetails,
              null,
              userDetails.getAuthorities()
            );
            org.springframework.security.core.context.SecurityContextHolder.getContext().setAuthentication(
              authToken
            );
          } catch (Exception e) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json");
            response.getWriter().write("{\"error\": \"Invalid or expired token\"}");
            return;
          }
        } else if (
          !uri.startsWith("/api/auth") &&
          !publicGet &&
          !uri.startsWith("/api/ws") &&
          !uri.startsWith("/api/sockjs") &&
          !uri.startsWith("/api/v3/api-docs") &&
          !uri.startsWith("/api/online") &&
          !localUpload
        ) {
          response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
          response.setContentType("application/json");
          response.getWriter().write("{\"error\": \"Missing token\"}");
          return;
        }

        filterChain.doFilter(request, response);
      }
    };
  }

  @Bean
  public OncePerRequestFilter userVisitFilter() {
    return new OncePerRequestFilter() {
      @Override
      protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
      ) throws ServletException, IOException {
        var auth =
          org.springframework.security.core.context.SecurityContextHolder.getContext().getAuthentication();
        if (
          auth != null &&
          auth.isAuthenticated() &&
          !(auth instanceof
              org.springframework.security.authentication.AnonymousAuthenticationToken)
        ) {
          String key = CachingConfig.VISIT_CACHE_NAME + ":" + LocalDate.now();
          redisTemplate.opsForSet().add(key, auth.getName());
        }
        filterChain.doFilter(request, response);
      }
    };
  }
}
