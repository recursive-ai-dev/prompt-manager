"""Tests for multi-provider LLM inference engine and catalog."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from prompt_manager.core.keychain import KeyVault
from prompt_manager.integrations.llm_providers import (
    MODEL_CATALOG,
    LLMClient,
    LLMRequest,
    LLMResponse,
    get_model_info,
    list_models_by_provider,
)


class TestLLMProviders(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_path = Path(self.temp_dir.name) / "vault.dat"
        self.vault = KeyVault(use_keyring=False, vault_path=self.vault_path)
        self.vault.set_api_key("openai", "sk-mock-key")
        self.vault.set_api_key("anthropic", "sk-ant-mock-key")
        self.vault.set_api_key("gemini", "mock-gemini-key")
        self.client = LLMClient(self.vault)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_model_catalog_structure(self):
        self.assertGreater(len(MODEL_CATALOG), 5)
        openai_models = list_models_by_provider("openai")
        self.assertTrue(any(m.id == "openai:gpt-4o" for m in openai_models))

        anthropic_models = list_models_by_provider("anthropic")
        self.assertTrue(any("claude" in m.id for m in anthropic_models))

    def test_get_model_info(self):
        info = get_model_info("openai:gpt-4o")
        self.assertIsNotNone(info)
        self.assertEqual(info.provider, "openai")
        self.assertGreater(info.cost_per_1k_input, 0)

    @patch("prompt_manager.integrations.llm_providers.PollinationsClient.generate")
    def test_pollinations_execution(self, mock_generate):
        mock_generate.return_value = "Pollinations mock response"
        req = LLMRequest(
            prompt="Hello AI",
            model_id="pollinations:openai-fast",
        )
        resp = self.client.execute(req)
        self.assertTrue(resp.is_success)
        self.assertEqual(resp.content, "Pollinations mock response")
        self.assertEqual(resp.estimated_cost_usd, 0.0)
        self.assertGreater(resp.total_tokens, 0)

    def test_missing_api_key_returns_error(self):
        empty_vault_path = Path(self.temp_dir.name) / "empty_vault.dat"
        empty_vault = KeyVault(use_keyring=False, vault_path=empty_vault_path)
        empty_client = LLMClient(empty_vault)
        req = LLMRequest(
            prompt="Hello OpenAI",
            model_id="openai:gpt-4o",
        )
        resp = empty_client.execute(req)
        self.assertFalse(resp.is_success)
        self.assertIn("API key not configured", resp.error)


if __name__ == "__main__":
    unittest.main()
