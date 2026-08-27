from unittest.mock import patch

import engine_capabilities


def test_capability_audit_does_not_claim_original_marker_stub_is_working():
    result = engine_capabilities.get_engine_capabilities()

    assert result["parsers"]["marker_gpu"]["implemented"] is False
    assert result["parsers"]["marker_cpu"]["implemented"] is False
    assert "marker_parser_not_implemented_in_original_source" in result["original_source_limitations"]
    assert "marker_parser_not_implemented_in_original_source" not in result["missing_full_restore"]


def test_full_restore_requires_mineru_llm_and_embedding_configuration():
    with (
        patch.object(engine_capabilities.config, "MINERU_API_KEY", ""),
        patch.object(engine_capabilities.config, "LLM_API_KEY", ""),
        patch.object(engine_capabilities.config, "EMBEDDING_API_KEY", ""),
    ):
        result = engine_capabilities.get_engine_capabilities()

    assert result["full_restore_ready"] is False
    assert "MINERU_API_KEY" in result["missing_full_restore"]
    assert "LLM_API_KEY" in result["missing_full_restore"]
    assert "EMBEDDING_API_KEY" in result["missing_full_restore"]
