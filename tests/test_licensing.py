"""Tests for Cryptographic Licensing and Pro tier engine."""

from datetime import datetime, timedelta
import unittest
from prompt_manager.core.licensing import (
    FEATURE_ARENA,
    FEATURE_HUD,
    LicenseManager,
    generate_license_key,
    verify_license_key,
)


class TestLicensing(unittest.TestCase):

    def test_generate_and_verify_valid_lifetime_license(self):
        key = generate_license_key(
            holder_name="Jane Doe",
            holder_email="jane@example.com",
            tier="pro_lifetime",
        )
        is_valid, reason, payload = verify_license_key(key)
        self.assertTrue(is_valid)
        self.assertEqual(reason, "Valid license")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["name"], "Jane Doe")
        self.assertEqual(payload["email"], "jane@example.com")
        self.assertEqual(payload["tier"], "pro_lifetime")
        self.assertEqual(payload["expires"], "never")

    def test_tampered_license_signature_fails(self):
        key = generate_license_key(
            holder_name="Hacker",
            holder_email="hacker@evil.com",
            tier="pro_lifetime",
        )
        # Modify the last character of signature
        tampered = key[:-1] + ("0" if key[-1] != "0" else "1")
        is_valid, reason, payload = verify_license_key(tampered)
        self.assertFalse(is_valid)
        self.assertIn("signature verification failed", reason.lower())

    def test_expired_license_fails(self):
        past_date = (datetime.now() - timedelta(days=5)).isoformat()
        key = generate_license_key(
            holder_name="Expired User",
            holder_email="expired@example.com",
            tier="pro_annual",
            expires_at=past_date,
        )
        is_valid, reason, payload = verify_license_key(key)
        self.assertFalse(is_valid)
        self.assertIn("expired", reason.lower())

    def test_license_manager_activation(self):
        mgr = LicenseManager()
        key = generate_license_key("Test Corp", "test@corp.com", tier="team")
        success, msg = mgr.activate_key(key)
        self.assertTrue(success)

        status = mgr.get_status()
        self.assertTrue(status.is_pro)
        self.assertEqual(status.tier, "team")
        self.assertTrue(mgr.is_feature_enabled(FEATURE_ARENA))
        self.assertTrue(mgr.is_feature_enabled(FEATURE_HUD))

        mgr.deactivate_key()
        status_after = mgr.get_status()
        self.assertNotEqual(status_after.tier, "team")


if __name__ == "__main__":
    unittest.main()
