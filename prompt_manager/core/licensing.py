"""Cryptographic offline-first licensing and Pro tier manager for Prompt Manager.

Validates digital license keys completely offline using HMAC-SHA256 signatures,
supports 14-day automatic local Pro trials, and manages feature access control.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import hmac
import json
from typing import Any, Dict, List, Optional, Tuple

from prompt_manager.config import get_setting, set_setting

# Digital signature secret root for Prompt Manager Studio offline licensing
# In production build, this can be combined with build-time hashes
_LICENSE_HMAC_SECRET = b"prompt-manager-studio-pro-v2-licensing-master-key-2026"

FEATURE_ARENA = "arena"
FEATURE_HUD = "hud"
FEATURE_TEAM_SYNC = "team_sync"
FEATURE_ADVANCED_EXPORTS = "advanced_exports"
FEATURE_ALL_THEMES = "all_themes"
FEATURE_UNLIMITED_PROMPTS = "unlimited_prompts"

ALL_PRO_FEATURES = [
    FEATURE_ARENA,
    FEATURE_HUD,
    FEATURE_TEAM_SYNC,
    FEATURE_ADVANCED_EXPORTS,
    FEATURE_ALL_THEMES,
    FEATURE_UNLIMITED_PROMPTS,
]

TRIAL_DURATION_DAYS = 14


@dataclass
class LicenseInfo:
    """Detailed metadata for the active application license or trial."""

    is_active: bool = False
    is_pro: bool = False
    is_trial: bool = False
    tier: str = "free"  # "free", "trial", "pro_lifetime", "pro_annual", "team"
    license_id: str = ""
    holder_name: str = ""
    holder_email: str = ""
    issued_at: str = ""
    expires_at: str = ""  # "never" or ISO timestamp
    days_remaining: int = 0
    features: List[str] = field(default_factory=list)
    status_message: str = "Free Community Edition"


def _canonical_json(data: Dict[str, Any]) -> bytes:
    """Format dictionary as canonical deterministic UTF-8 bytes for signing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _compute_signature(payload_bytes: bytes) -> str:
    """Generate truncated HMAC-SHA256 hex signature for license verification."""
    mac = hmac.new(_LICENSE_HMAC_SECRET, payload_bytes, hashlib.sha256).hexdigest()
    return mac[:32]  # 32-char hex string


def generate_license_key(
    holder_name: str,
    holder_email: str,
    tier: str = "pro_lifetime",
    expires_at: str = "never",
    features: Optional[List[str]] = None,
    license_id: Optional[str] = None,
) -> str:
    """Generate a signed cryptographic license key string.

    Format: PM-<TIER>-<BASE64_PAYLOAD>.<SIGNATURE>
    """
    if features is None:
        features = list(ALL_PRO_FEATURES)

    if not license_id:
        import uuid
        license_id = f"PM-{tier.upper()[:3]}-{uuid.uuid4().hex[:8].upper()}"

    payload = {
        "id": license_id,
        "name": holder_name.strip(),
        "email": holder_email.strip(),
        "tier": tier,
        "issued": datetime.now().isoformat(),
        "expires": expires_at,
        "features": features,
    }

    payload_bytes = _canonical_json(payload)
    b64_payload = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    sig = _compute_signature(payload_bytes)

    tier_prefix = tier.upper().replace("_", "-")
    return f"PM-{tier_prefix}-{b64_payload}.{sig}"


def verify_license_key(key: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Cryptographically verify a license key offline.

    Returns:
        (is_valid, error_reason_or_ok, payload_dict)
    """
    if not key or not isinstance(key, str):
        return False, "Empty license key", None

    clean_key = key.strip()
    if not clean_key.startswith("PM-") or "." not in clean_key:
        return False, "Invalid license key format", None

    try:
        header_body, sig = clean_key.rsplit(".", 1)
        # format: PM-<TIER>-<B64>
        if "-" not in header_body:
            return False, "Malformed license header structure", None

        prefix, b64_payload = header_body.rsplit("-", 1)
        if not prefix.startswith("PM-") or not b64_payload:
            return False, "Malformed license header structure", None

        # Add back required base64 padding
        padding = 4 - (len(b64_payload) % 4)
        if padding != 4:
            b64_payload += "=" * padding

        payload_bytes = base64.urlsafe_b64decode(b64_payload.encode("ascii"))
        expected_sig = _compute_signature(payload_bytes)

        if not hmac.compare_digest(sig.lower(), expected_sig.lower()):
            return False, "Digital signature verification failed (invalid or tampered key)", None

        payload = json.loads(payload_bytes.decode("utf-8"))

        # Check expiration date if not lifetime ("never")
        expires = payload.get("expires", "never")
        if expires != "never":
            try:
                exp_date = datetime.fromisoformat(expires)
                if datetime.now() > exp_date:
                    return False, f"License expired on {exp_date.strftime('%Y-%m-%d')}", payload
            except Exception:
                return False, "Malformed expiration timestamp in license", None

        return True, "Valid license", payload
    except Exception as e:
        return False, f"License parse error: {e}", None


# ── License Manager & Feature Gate ──────────────────────────────────────


class LicenseManager:
    """Stateful license manager querying settings, verifying status, and managing trial."""

    def __init__(self):
        self._ensure_trial_initialized()

    def _ensure_trial_initialized(self) -> None:
        """Initialize trial timestamp on first run if not present."""
        trial_start = get_setting("trial_start_date")
        if not trial_start:
            now_iso = datetime.now().isoformat()
            set_setting("trial_start_date", now_iso)

    def get_status(self) -> LicenseInfo:
        """Return the current active license status, trial, or free tier info."""
        key = get_setting("license_key", "")
        if key:
            is_valid, reason, payload = verify_license_key(key)
            if is_valid and payload:
                tier = payload.get("tier", "pro_lifetime")
                expires = payload.get("expires", "never")
                days_left = 99999
                if expires != "never":
                    try:
                        exp_dt = datetime.fromisoformat(expires)
                        days_left = max(0, (exp_dt - datetime.now()).days)
                    except Exception:
                        pass

                return LicenseInfo(
                    is_active=True,
                    is_pro=True,
                    is_trial=False,
                    tier=tier,
                    license_id=payload.get("id", ""),
                    holder_name=payload.get("name", ""),
                    holder_email=payload.get("email", ""),
                    issued_at=payload.get("issued", ""),
                    expires_at=expires,
                    days_remaining=days_left,
                    features=payload.get("features", ALL_PRO_FEATURES),
                    status_message=f"Active Pro ({tier.replace('_', ' ').title()})",
                )
            else:
                # Key present but invalid or expired
                pass

        # Check Trial Status
        trial_start_str = get_setting("trial_start_date", "")
        if trial_start_str:
            try:
                start_dt = datetime.fromisoformat(trial_start_str)
                elapsed_days = (datetime.now() - start_dt).total_seconds() / 86400.0
                days_left = max(0, int(TRIAL_DURATION_DAYS - elapsed_days))
                if days_left > 0:
                    return LicenseInfo(
                        is_active=True,
                        is_pro=True,
                        is_trial=True,
                        tier="trial",
                        license_id="TRIAL-EVALUATION",
                        holder_name="Evaluation User",
                        holder_email="",
                        issued_at=trial_start_str,
                        expires_at=(start_dt + timedelta(days=TRIAL_DURATION_DAYS)).isoformat(),
                        days_remaining=days_left,
                        features=list(ALL_PRO_FEATURES),
                        status_message=f"Pro Evaluation Trial ({days_left} days remaining)",
                    )
            except Exception:
                pass

        # Default Community Edition (Free)
        return LicenseInfo(
            is_active=False,
            is_pro=False,
            is_trial=False,
            tier="free",
            features=[],
            status_message="Free Community Edition",
        )

    def activate_key(self, key: str) -> Tuple[bool, str]:
        """Validate and store a new license key in persistent settings."""
        is_valid, reason, payload = verify_license_key(key)
        if not is_valid:
            return False, reason
        set_setting("license_key", key.strip())
        return True, f"Successfully activated {payload.get('tier', 'Pro').title()} license!"

    def deactivate_key(self) -> None:
        """Remove active license key and revert to trial/community tier."""
        set_setting("license_key", "")

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific commercial feature is currently authorized."""
        status = self.get_status()
        if status.is_pro:
            return feature_name in status.features
        return False


# Singleton License Manager
_global_license_manager: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    """Return singleton LicenseManager instance."""
    global _global_license_manager
    if _global_license_manager is None:
        _global_license_manager = LicenseManager()
    return _global_license_manager
