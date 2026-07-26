package com.openisle.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Arrays;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

class AiScreeningClientTest {

  @Test
  void marksConfigurationConstructorForSpringInjection() {
    var injectedConstructors = Arrays
      .stream(AiScreeningClient.class.getDeclaredConstructors())
      .filter(constructor -> constructor.isAnnotationPresent(Autowired.class))
      .toList();

    assertThat(injectedConstructors).hasSize(1);
    assertThat(injectedConstructors.get(0).getParameterCount()).isEqualTo(3);
  }
}
