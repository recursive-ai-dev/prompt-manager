"""Tests for Keychain and secure credential storage."""

import unittest
from prompt_manager.core.keychain import KeyVault, _xor_cipher


class TestKeyVault(unittest.TestCase):

    def setUp(self):
        # Force fallback vault for isolated unit testing
        self.vault = KeyVault(use_keyring=False)

    def test_set_and_get_api_key(self):
        self.vault.set_api_key("openai", "sk-test-12345")
        retrieved = self.vault.get_api_key("openai")
        self.assertEqual(retrieved, "sk-test-12345")

    def test_delete_api_key(self):
        self.vault.set_api_key("anthropic", "sk-ant-999")
        self.assertEqual(self.vault.get_api_key("anthropic"), "sk-ant-999")
        self.vault.delete_api_key("anthropic")
        self.assertEqual(self.vault.get_api_key("anthropic"), "")

    def test_provider_config(self):
        self.vault.set_provider_config("ollama", {"base_url": "http://127.0.0.1:11434", "default_model": "llama3.2"})
        cfg = self.vault.get_provider_config("ollama")
        self.assertEqual(cfg.get("base_url"), "http://127.0.0.1:11434")
        self.assertEqual(cfg.get("default_model"), "llama3.2")

    def test_xor_cipher_symmetry(self):
        msg = b"secret-payload-data-to-protect"
        key = b"encryption-key-123"
        enc = _xor_cipher(msg, key)
        self.assertNotEqual(enc, msg)
        dec = _xor_cipher(enc, key)
        self.assertEqual(dec, msg)


if __name__ == "__main__":
    unittest.main()
