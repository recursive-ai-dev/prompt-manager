"""Comprehensive Settings and API Key Management Dialog."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from prompt_manager.config import (
    APP_CONFIG_DIR,
    APP_DATA_DIR,
    APP_DISPLAY_NAME,
    APP_VERSION,
    DATABASE_PATH,
    DEFAULT_TARGET_MODELS,
    get_setting,
    get_theme_id,
    set_setting,
    set_theme_id,
)
from prompt_manager.core.keychain import get_key_vault
from prompt_manager.core.licensing import (
    ALL_PRO_FEATURES,
    generate_license_key,
    get_license_manager,
    verify_license_key,
)
from prompt_manager.integrations.llm_providers import (
    LLMClient,
    LLMRequest,
    discover_ollama_models,
)
from prompt_manager.ui.theme import THEME_IDS, list_themes


class SettingsDialog(QDialog):
    """Centralized preferences and BYOK API key configuration dialog."""

    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings & Provider Configuration")
        self.resize(650, 500)
        self.vault = get_key_vault()
        self.lic_mgr = get_license_manager()

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()

        # ── Tab 1: General Preferences ───────────────────────────────
        general_tab = QWidget()
        gen_layout = QVBoxLayout(general_tab)
        gen_layout.setSpacing(12)

        pref_group = QGroupBox("Interface & Defaults")
        pref_form = QFormLayout(pref_group)
        pref_form.setSpacing(10)

        # Theme Selector
        self.theme_combo = QComboBox()
        for t in list_themes():
            self.theme_combo.addItem(f"{t.name} ({t.variant})", t.id)
        curr_theme = get_theme_id()
        idx = self.theme_combo.findData(curr_theme)
        if idx != -1:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        pref_form.addRow("UI Theme:", self.theme_combo)

        # Default Model
        self.default_model_combo = QComboBox()
        for m in DEFAULT_TARGET_MODELS:
            self.default_model_combo.addItem(m, m)
        pref_form.addRow("Default Target Model:", self.default_model_combo)

        # Default Temperature
        temp_row = QHBoxLayout()
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 150)
        self.temp_slider.setValue(70)
        self.temp_label = QLabel("0.70")
        self.temp_label.setStyleSheet("min-width: 30px; font-weight: 600;")
        self.temp_slider.valueChanged.connect(lambda v: self.temp_label.setText(f"{v/100:.2f}"))
        temp_row.addWidget(self.temp_slider)
        temp_row.addWidget(self.temp_label)
        pref_form.addRow("Default Temperature:", temp_row)

        gen_layout.addWidget(pref_group)

        # Storage paths info
        storage_group = QGroupBox("Local Storage & Database")
        storage_layout = QVBoxLayout(storage_group)
        db_info = QLabel(f"Database: {DATABASE_PATH}\nConfig: {APP_CONFIG_DIR}")
        db_info.setStyleSheet("font-family: monospace; font-size: 11px; color: #94a3b8;")
        storage_layout.addWidget(db_info)

        btn_row = QHBoxLayout()
        open_folder_btn = QPushButton("📁 Open Data Folder")
        open_folder_btn.clicked.connect(self._open_data_folder)
        btn_row.addWidget(open_folder_btn)
        btn_row.addStretch()
        storage_layout.addLayout(btn_row)

        gen_layout.addWidget(storage_group)
        gen_layout.addStretch()
        self.tabs.addTab(general_tab, "⚙ General")

        # ── Tab 2: BYOK AI Providers ────────────────────────────────
        providers_tab = QWidget()
        prov_layout = QVBoxLayout(providers_tab)
        prov_layout.setSpacing(10)

        prov_header = QLabel("Configure your API keys for direct execution in the Multi-Model Arena.\nKeys are stored in your secure OS keyring / encrypted local vault.")
        prov_header.setStyleSheet("font-size: 11px; color: #94a3b8;")
        prov_layout.addWidget(prov_header)

        form_group = QGroupBox("Frontier & Local Providers")
        prov_form = QFormLayout(form_group)
        prov_form.setSpacing(8)

        # OpenAI
        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key_edit.setPlaceholderText("sk-proj-...")
        oa_row = QHBoxLayout()
        oa_row.addWidget(self.openai_key_edit, stretch=1)
        oa_test_btn = QPushButton("Test")
        oa_test_btn.clicked.connect(lambda: self._test_provider_key("openai"))
        oa_row.addWidget(oa_test_btn)
        prov_form.addRow("OpenAI API Key:", oa_row)

        # Anthropic
        self.anthropic_key_edit = QLineEdit()
        self.anthropic_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthropic_key_edit.setPlaceholderText("sk-ant-...")
        ant_row = QHBoxLayout()
        ant_row.addWidget(self.anthropic_key_edit, stretch=1)
        ant_test_btn = QPushButton("Test")
        ant_test_btn.clicked.connect(lambda: self._test_provider_key("anthropic"))
        ant_row.addWidget(ant_test_btn)
        prov_form.addRow("Anthropic API Key:", ant_row)

        # Google Gemini
        self.gemini_key_edit = QLineEdit()
        self.gemini_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key_edit.setPlaceholderText("AIzaSy...")
        gem_row = QHBoxLayout()
        gem_row.addWidget(self.gemini_key_edit, stretch=1)
        gem_test_btn = QPushButton("Test")
        gem_test_btn.clicked.connect(lambda: self._test_provider_key("gemini"))
        gem_row.addWidget(gem_test_btn)
        prov_form.addRow("Google Gemini Key:", gem_row)

        # Ollama Local Endpoint
        self.ollama_url_edit = QLineEdit()
        self.ollama_url_edit.setPlaceholderText("http://localhost:11434")
        ollama_row = QHBoxLayout()
        ollama_row.addWidget(self.ollama_url_edit, stretch=1)
        ollama_test_btn = QPushButton("Test Ollama")
        ollama_test_btn.clicked.connect(self._test_ollama)
        ollama_row.addWidget(ollama_test_btn)
        prov_form.addRow("Ollama Local URL:", ollama_row)

        # OpenRouter
        self.openrouter_key_edit = QLineEdit()
        self.openrouter_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.openrouter_key_edit.setPlaceholderText("sk-or-...")
        or_row = QHBoxLayout()
        or_row.addWidget(self.openrouter_key_edit, stretch=1)
        or_test_btn = QPushButton("Test")
        or_test_btn.clicked.connect(lambda: self._test_provider_key("openrouter"))
        or_row.addWidget(or_test_btn)
        prov_form.addRow("OpenRouter Key:", or_row)

        prov_layout.addWidget(form_group)
        prov_layout.addStretch()
        self.tabs.addTab(providers_tab, "🔑 API Keys & BYOK")

        # ── Tab 3: Pro License & Features ───────────────────────────
        lic_tab = QWidget()
        lic_layout = QVBoxLayout(lic_tab)
        lic_layout.setSpacing(12)

        # Status Card
        self.lic_status_frame = QFrame()
        self.lic_status_frame.setStyleSheet("background: #1e293b; border-radius: 8px; padding: 12px;")
        sf_layout = QVBoxLayout(self.lic_status_frame)
        sf_layout.setSpacing(4)

        self.lic_badge = QLabel("✨ PRO ACTIVE")
        self.lic_badge.setStyleSheet("font-size: 14px; font-weight: 700; color: #10b981;")
        sf_layout.addWidget(self.lic_badge)

        self.lic_detail_label = QLabel("License: Valid Lifetime License")
        self.lic_detail_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        sf_layout.addWidget(self.lic_detail_label)
        lic_layout.addWidget(self.lic_status_frame)

        # License Key Form
        key_group = QGroupBox("Activate License Key")
        key_form = QVBoxLayout(key_group)
        key_form.setSpacing(8)

        self.license_key_input = QLineEdit()
        self.license_key_input.setPlaceholderText("Paste your PM-PRO-... license key here")
        key_form.addWidget(self.license_key_input)

        act_btn_row = QHBoxLayout()
        self.activate_btn = QPushButton("✨ Activate License")
        self.activate_btn.setObjectName("primaryButton")
        self.activate_btn.clicked.connect(self._activate_license)
        act_btn_row.addWidget(self.activate_btn)

        self.deactivate_btn = QPushButton("Deactivate")
        self.deactivate_btn.clicked.connect(self._deactivate_license)
        act_btn_row.addWidget(self.deactivate_btn)
        act_btn_row.addStretch()

        key_form.addLayout(act_btn_row)
        lic_layout.addWidget(key_group)

        # Features list
        perks_group = QGroupBox("Pro Edition Features")
        perks_layout = QVBoxLayout(perks_group)
        perks_text = QLabel(
            "✓ Multi-Model Evaluation Arena (Side-by-side LLM benchmark)\n"
            "✓ Global Spotlight/Raycast Quick Launcher HUD\n"
            "✓ Zero-Trust Local Storage & OS Keyring API Key Vault\n"
            "✓ Unlimited Prompts, Revisions & Fast FTS5 Search\n"
            "✓ All 13 Handcrafted Themes & Export Formats"
        )
        perks_text.setStyleSheet("font-size: 11px; color: #cbd5e1; line-height: 1.6;")
        perks_layout.addWidget(perks_text)
        lic_layout.addWidget(perks_group)

        lic_layout.addStretch()
        self.tabs.addTab(lic_tab, "✨ License & Pro")

        main_layout.addWidget(self.tabs)

        # ── Bottom Action Buttons ────────────────────────────────────
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._save_and_close)
        bottom_row.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        bottom_row.addWidget(self.cancel_btn)

        main_layout.addLayout(bottom_row)

    def _load_values(self):
        # Load API keys from vault
        self.openai_key_edit.setText(self.vault.get_api_key("openai"))
        self.anthropic_key_edit.setText(self.vault.get_api_key("anthropic"))
        self.gemini_key_edit.setText(self.vault.get_api_key("gemini"))
        self.openrouter_key_edit.setText(self.vault.get_api_key("openrouter"))

        ollama_cfg = self.vault.get_provider_config("ollama")
        self.ollama_url_edit.setText(ollama_cfg.get("base_url", "http://localhost:11434"))

        # License status
        self._refresh_license_display()

    def _refresh_license_display(self):
        status = self.lic_mgr.get_status()
        if status.is_pro and not status.is_trial:
            self.lic_badge.setText(f"✨ PRO ACTIVE ({status.tier.upper()})")
            self.lic_badge.setStyleSheet("font-size: 14px; font-weight: 700; color: #10b981;")
            self.lic_detail_label.setText(f"Licensed to: {status.holder_name} ({status.holder_email})\nLicense ID: {status.license_id}")
            self.deactivate_btn.show()
        elif status.is_trial:
            self.lic_badge.setText(f"⚡ PRO EVALUATION TRIAL ({status.days_remaining} days left)")
            self.lic_badge.setStyleSheet("font-size: 14px; font-weight: 700; color: #38bdf8;")
            self.lic_detail_label.setText(f"Full Pro features enabled for evaluation until trial expiration.")
            self.deactivate_btn.hide()
        else:
            self.lic_badge.setText("🔓 FREE COMMUNITY EDITION")
            self.lic_badge.setStyleSheet("font-size: 14px; font-weight: 700; color: #94a3b8;")
            self.lic_detail_label.setText("Activate a Pro license key to unlock Multi-Model Arena, HUD & Advanced features.")
            self.deactivate_btn.hide()

    def _on_theme_changed(self):
        theme_id = self.theme_combo.currentData()
        if theme_id:
            set_theme_id(theme_id)
            self.theme_changed.emit(theme_id)

    def _open_data_folder(self):
        QDesktopServices.openUrl(DATABASE_PATH.parent.as_uri())

    def _test_provider_key(self, provider: str):
        key_map = {
            "openai": self.openai_key_edit.text().strip(),
            "anthropic": self.anthropic_key_edit.text().strip(),
            "gemini": self.gemini_key_edit.text().strip(),
            "openrouter": self.openrouter_key_edit.text().strip(),
        }
        key = key_map.get(provider, "")
        if not key:
            QMessageBox.warning(self, "API Key Missing", f"Please enter a key for {provider.title()} first.")
            return

        # Save temporarily in vault to test
        self.vault.set_api_key(provider, key)
        client = LLMClient(self.vault)
        model_map = {
            "openai": "openai:gpt-4o-mini",
            "anthropic": "anthropic:claude-3-5-haiku-20241022",
            "gemini": "gemini:gemini-2.5-flash",
            "openrouter": "openrouter:openrouter/auto",
        }
        model_id = model_map.get(provider, "pollinations:openai-fast")

        req = LLMRequest(prompt="Say 'Connected successfully!' in 3 words.", model_id=model_id, timeout=15)
        resp = client.execute(req)

        if resp.is_success:
            QMessageBox.information(
                self,
                "Connection Test Passed",
                f"✅ {provider.title()} connection verified successfully!\n\nModel: {resp.model_id}\nResponse: \"{resp.content}\"\nLatency: {resp.elapsed_seconds:.2f}s",
            )
        else:
            QMessageBox.critical(
                self,
                "Connection Failed",
                f"❌ Could not connect to {provider.title()}:\n\n{resp.error}",
            )

    def _test_ollama(self):
        url = self.ollama_url_edit.text().strip() or "http://localhost:11434"
        models = discover_ollama_models(url)
        if models:
            names = ", ".join(m.display_name.replace("Ollama: ", "").replace(" (Local)", "") for m in models)
            QMessageBox.information(
                self,
                "Ollama Connected",
                f"✅ Connected to Ollama at {url}!\n\nDiscovered {len(models)} local models:\n{names}",
            )
        else:
            QMessageBox.warning(
                self,
                "Ollama Response",
                f"Connected to {url}, but found 0 models installed. Run `ollama pull llama3.2` to download a model.",
            )

    def _activate_license(self):
        key = self.license_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Missing Key", "Please paste your license key.")
            return

        success, msg = self.lic_mgr.activate_key(key)
        if success:
            QMessageBox.information(self, "License Activated", f"🎉 {msg}")
            self.license_key_input.clear()
            self._refresh_license_display()
        else:
            QMessageBox.critical(self, "Activation Failed", f"❌ {msg}")

    def _deactivate_license(self):
        reply = QMessageBox.question(
            self,
            "Deactivate License",
            "Are you sure you want to deactivate this license key?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.lic_mgr.deactivate_key()
            self._refresh_license_display()

    def _save_and_close(self):
        # Persist API keys
        self.vault.set_api_key("openai", self.openai_key_edit.text().strip())
        self.vault.set_api_key("anthropic", self.anthropic_key_edit.text().strip())
        self.vault.set_api_key("gemini", self.gemini_key_edit.text().strip())
        self.vault.set_api_key("openrouter", self.openrouter_key_edit.text().strip())

        ollama_url = self.ollama_url_edit.text().strip() or "http://localhost:11434"
        self.vault.set_provider_config("ollama", {"base_url": ollama_url})

        self.accept()
