"""Secure API key and credential vault for Prompt Manager.

Provides safe credential persistence using the system keyring service (via `keyring`),
with a robust encrypted/obfuscated local fallback store for headless or unsupported environments.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from prompt_manager.config import APP_CONFIG_DIR, ensure_directories

KEYRING_SERVICE_NAME = "prompt-manager"
VAULT_FILE_PATH = APP_CONFIG_DIR / "vault.dat"

# Standard LLM providers supported by Prompt Manager
SUPPORTED_PROVIDERS = [
    "openai",
    "anthropic",
    "gemini",
    "ollama",
    "openrouter",
    "pollinations",
]


def _get_machine_seed() -> bytes:
    """Generate a stable machine/user-bound key derivation seed."""
    try:
        user = os.environ.get("USER", os.environ.get("USERNAME", "default_user"))
        home = str(Path.home())
        machine_id = ""
        # On Linux /etc/machine-id, on others fallback
        for mid_path in [Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")]:
            if mid_path.exists():
                try:
                    machine_id = mid_path.read_text().strip()
                    break
                except Exception:
                    pass
        raw = f"{user}::{home}::{machine_id}::prompt-manager-v2"
        return hashlib.sha256(raw.encode("utf-8")).digest()
    except Exception:
        return hashlib.sha256(b"prompt-manager-fallback-seed").digest()


def _xor_cipher(data: bytes, key: bytes) -> bytes:
    """Symmetric XOR stream cipher with key expansion."""
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))


class KeyVault:
    """Secure credential manager supporting OS keyring and encrypted fallback storage."""

    def __init__(self, use_keyring: bool = True, vault_path: Optional[Path] = None):
        self._use_keyring = use_keyring
        self._keyring_available: Optional[bool] = None
        self.vault_path = vault_path or VAULT_FILE_PATH

    def _check_keyring(self) -> bool:
        if self._keyring_available is not None:
            return self._keyring_available
        if not self._use_keyring:
            self._keyring_available = False
            return False
        try:
            import keyring
            # Test getting a dummy key to verify backend works
            keyring.get_password(KEYRING_SERVICE_NAME, "__test_probe__")
            self._keyring_available = True
        except Exception:
            self._keyring_available = False
        return self._keyring_available

    # ── Fallback local encrypted store ──────────────────────────────────

    def _read_fallback_vault(self) -> Dict[str, Any]:
        """Read and decrypt the local fallback vault."""
        if not self.vault_path.exists():
            return {}
        try:
            encrypted = self.vault_path.read_bytes()
            if not encrypted:
                return {}
            seed = _get_machine_seed()
            decrypted = _xor_cipher(encrypted, seed)
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            return {}

    def _write_fallback_vault(self, data: Dict[str, Any]) -> None:
        """Encrypt and persist the local fallback vault with restricted permissions (0600)."""
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.vault_path.parent, 0o700)
        except Exception:
            pass

        seed = _get_machine_seed()
        serialized = json.dumps(data).encode("utf-8")
        encrypted = _xor_cipher(serialized, seed)

        temp_path = self.vault_path.with_suffix(".tmp")
        fd = os.open(str(temp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with open(fd, "wb") as f:
                f.write(encrypted)
        except Exception:
            os.close(fd)
            raise
        temp_path.replace(self.vault_path)
        try:
            os.chmod(self.vault_path, 0o600)
        except Exception:
            pass

    # ── Core Key Operations ─────────────────────────────────────────────

    def get_api_key(self, provider: str) -> str:
        """Retrieve stored API key for the given provider."""
        provider = provider.lower().strip()
        if self._check_keyring():
            try:
                import keyring
                val = keyring.get_password(KEYRING_SERVICE_NAME, f"api_key_{provider}")
                if val:
                    return val.strip()
            except Exception:
                pass
        
        # Fallback to local encrypted vault
        vault = self._read_fallback_vault()
        return str(vault.get(f"api_key_{provider}", "")).strip()

    def set_api_key(self, provider: str, key: str) -> None:
        """Store API key for the given provider."""
        provider = provider.lower().strip()
        clean_key = key.strip()
        
        if self._check_keyring():
            try:
                import keyring
                if clean_key:
                    keyring.set_password(KEYRING_SERVICE_NAME, f"api_key_{provider}", clean_key)
                else:
                    try:
                        keyring.delete_password(KEYRING_SERVICE_NAME, f"api_key_{provider}")
                    except Exception:
                        pass
            except Exception:
                pass

        # Also mirror/store in local encrypted vault for consistency
        vault = self._read_fallback_vault()
        if clean_key:
            vault[f"api_key_{provider}"] = clean_key
        else:
            vault.pop(f"api_key_{provider}", None)
        self._write_fallback_vault(vault)

    def delete_api_key(self, provider: str) -> None:
        """Delete stored API key for the given provider."""
        self.set_api_key(provider, "")

    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get full provider configuration (endpoint, default model, etc.)."""
        provider = provider.lower().strip()
        vault = self._read_fallback_vault()
        cfg = vault.get(f"config_{provider}", {})
        if not isinstance(cfg, dict):
            cfg = {}
        # Inject the API key into config dict
        cfg["api_key"] = self.get_api_key(provider)
        # Default endpoint for Ollama if missing
        if provider == "ollama" and not cfg.get("base_url"):
            cfg["base_url"] = "http://localhost:11434"
        return cfg

    def set_provider_config(self, provider: str, config: Dict[str, Any]) -> None:
        """Update provider configuration settings."""
        provider = provider.lower().strip()
        cfg_copy = dict(config)
        api_key = cfg_copy.pop("api_key", None)
        if api_key is not None:
            self.set_api_key(provider, str(api_key))

        vault = self._read_fallback_vault()
        vault[f"config_{provider}"] = cfg_copy
        self._write_fallback_vault(vault)

    def list_configured_providers(self) -> List[str]:
        """Return list of providers with non-empty API keys or configured endpoints."""
        configured = []
        for p in SUPPORTED_PROVIDERS:
            key = self.get_api_key(p)
            if key:
                configured.append(p)
            elif p == "ollama":
                # Ollama doesn't strictly require an API key
                cfg = self.get_provider_config("ollama")
                if cfg.get("base_url"):
                    configured.append("ollama")
        return configured


# Singleton instance
_global_vault: Optional[KeyVault] = None


def get_key_vault() -> KeyVault:
    """Return the global KeyVault instance."""
    global _global_vault
    if _global_vault is None:
        _global_vault = KeyVault()
    return _global_vault
