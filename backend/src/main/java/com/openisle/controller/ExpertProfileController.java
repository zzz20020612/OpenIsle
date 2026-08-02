package com.openisle.controller;

import com.openisle.dto.ExpertProfileDto;
import com.openisle.service.ExpertProfileService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/experts")
@RequiredArgsConstructor
@Tag(name = "Experts", description = "Expert profile APIs")
public class ExpertProfileController {

  private final ExpertProfileService expertProfileService;

  @GetMapping("/{expertId}")
  @Operation(summary = "Get expert profile", description = "Return expert identity and linked public papers.")
  public ExpertProfileDto getExpert(@PathVariable Long expertId) {
    return expertProfileService.getExpert(expertId);
  }
}
