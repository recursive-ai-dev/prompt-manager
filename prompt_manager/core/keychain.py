"""OS keyring credential storage, with read-only migration of legacy XOR vaults.

Persistent secrets require a supported OS keyring. Explicit use_keyring=False
provides an in-memory store for temporary connections and isolated tests.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional

from prompt_manager.config import APP_CONFIG_DIR

KEYRING_SERVICE_NAME = "prompt-manager"
VAULT_FILE_PATH = APP_CONFIG_DIR / "vault.dat"
_LOG = logging.getLogger(__name__)
_MIGRATION_LOCK = RLock()
_NATIVE_BACKENDS = {
    "keyring.backends.SecretService", "keyring.backends.kwallet",
    "keyring.backends.macOS", "keyring.backends.Windows",
    "keyring.backends.libsecret",
}


class CredentialStoreError(RuntimeError):
    """A credential could not be safely read, migrated, or persisted."""


SUPPORTED_PROVIDERS = [
    "openai",
    "anthropic",
    "gemini",
    "ollama",
    "openrouter",
    "pollinations",
]


def _get_machine_seed() -> bytes:
    """Reconstruct the old obfuscation seed for migration only; this is not a secret."""
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
                except OSError:
                    pass
        raw = f"{user}::{home}::{machine_id}::prompt-manager-v2"
        return hashlib.sha256(raw.encode("utf-8")).digest()
    except OSError:
        return hashlib.sha256(b"prompt-manager-fallback-seed").digest()


def _xor_cipher(data: bytes, key: bytes) -> bytes:
    """Decode the legacy vault for migration only. Never use for new storage."""
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))


class KeyVault:
    """Store secrets in a native OS keyring, never in an application disk file."""

    def __init__(self, use_keyring: bool = True, vault_path: Optional[Path] = None):
        self._use_keyring = use_keyring
        self.vault_path = vault_path or VAULT_FILE_PATH
        self._session: Dict[str, str] = {}

    def _backend(self, required: bool = False):
        try:
            import keyring
            backend = keyring.get_keyring()
            if type(backend).__module__ == "keyring.backends.chainer":
                backend = next(
                    b for b in backend.backends
                    if type(b).__module__ in _NATIVE_BACKENDS
                )
            if type(backend).__module__ not in _NATIVE_BACKENDS or backend.priority <= 0:
                raise ValueError("Unsupported backend")
            return backend
        except Exception:
            # Backends can fail with platform-specific exceptions. Do not include
            # their messages, which may contain sensitive arguments.
            message = "OS keyring unavailable. Enable or unlock a supported system keyring to save credentials."
            if required:
                raise CredentialStoreError(message) from None
            _LOG.warning(message)
            return None

    def _get(self, name: str) -> str:
        if not self._use_keyring:
            return self._session.get(name, "")
        backend = self._backend(required=self.vault_path.exists())
        if backend is None:
            return ""
        self._migrate_legacy(backend)
        try:
            return backend.get_password(KEYRING_SERVICE_NAME, name) or ""
        except Exception:
            raise CredentialStoreError("Could not read the OS keyring. Unlock it and retry.") from None

    def _set(self, name: str, value: str) -> None:
        if not self._use_keyring:
            if value:
                self._session[name] = value
            else:
                self._session.pop(name, None)
            return
        backend = self._backend(required=True)
        self._migrate_legacy(backend)
        try:
            if value:
                backend.set_password(KEYRING_SERVICE_NAME, name, value)
                if backend.get_password(KEYRING_SERVICE_NAME, name) != value:
                    raise ValueError("Write verification failed")
            elif backend.get_password(KEYRING_SERVICE_NAME, name) is not None:
                backend.delete_password(KEYRING_SERVICE_NAME, name)
        except Exception:
            raise CredentialStoreError("Could not save credentials in the OS keyring. Unlock it and retry.") from None

    def _migrate_legacy(self, backend) -> None:
        """Delete the old vault only after all entries are verified in the keyring."""
        with _MIGRATION_LOCK:
            if not self.vault_path.exists():
                return
            try:
                raw = self.vault_path.read_bytes()
                data = json.loads(_xor_cipher(raw, _get_machine_seed()).decode("utf-8")) if raw else {}
                if not isinstance(data, dict):
                    raise ValueError("Invalid legacy vault")
                for name, value in data.items():
                    if name.startswith("api_key_") and isinstance(value, str):
                        encoded = value
                    elif name.startswith("config_") and isinstance(value, dict):
                        encoded = json.dumps(value)
                    else:
                        raise ValueError("Unknown legacy entry")
                    # The keyring is authoritative if a newer value is already there.
                    existing = backend.get_password(KEYRING_SERVICE_NAME, name)
                    if existing is None:
                        backend.set_password(KEYRING_SERVICE_NAME, name, encoded)
                        if backend.get_password(KEYRING_SERVICE_NAME, name) != encoded:
                            raise ValueError("Migration verification failed")
                self.vault_path.unlink()
            except Exception:
                raise CredentialStoreError(
                    "Legacy vault migration failed; the original vault has been retained. "
                    "Unlock the OS keyring and retry."
                ) from None

    def get_api_key(self, provider: str) -> str:
        return self._get(f"api_key_{provider.lower().strip()}").strip()

    def set_api_key(self, provider: str, key: str) -> None:
        self._set(f"api_key_{provider.lower().strip()}", key.strip())

    def delete_api_key(self, provider: str) -> None:
        self.set_api_key(provider, "")

    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        provider = provider.lower().strip()
        raw = self._get(f"config_{provider}")
        try:
            cfg = json.loads(raw) if raw else {}
            if not isinstance(cfg, dict):
                raise ValueError("Invalid configuration")
        except (ValueError, TypeError):
            raise CredentialStoreError("Invalid provider configuration in the OS keyring.") from None
        cfg["api_key"] = self.get_api_key(provider)
        if provider == "ollama" and not cfg.get("base_url"):
            cfg["base_url"] = "http://localhost:11434"
        return cfg

    def set_provider_config(self, provider: str, config: Dict[str, Any]) -> None:
        provider = provider.lower().strip()
        cfg = dict(config)
        key = cfg.pop("api_key", None)
        if key is not None:
            self.set_api_key(provider, str(key))
        self._set(f"config_{provider}", json.dumps(cfg))

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
