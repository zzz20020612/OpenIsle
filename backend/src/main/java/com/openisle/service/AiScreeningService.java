package com.openisle.service;

import com.openisle.model.PaperProfile;
import lombok.RequiredArgsConstructor;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AiScreeningService {

  private final ApplicationEventPublisher eventPublisher;

  public void requestScreening(PaperProfile paper) {
    eventPublisher.publishEvent(new AiScreeningRequestedEvent(paper.getId()));
  }
}
