"""Tests for GitHub API client, git helper, and sync orchestration."""

import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from prompt_manager.core.github_sync import (
    push_library_via_api,
    pull_library_via_api,
    push_individual_prompts_via_api,
    validate_github_config,
)
from prompt_manager.core.models import Prompt
from prompt_manager.integrations.git_helper import (
    build_authenticated_remote_url,
    is_git_available,
)
from prompt_manager.integrations.github_client import (
    GithubClient,
    GithubError,
    _split_full_name,
)
from prompt_manager.storage.database import Database
from prompt_manager.storage.repository import PromptRepository


class TestGitHubIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db = Database(self.db_path)
        self.repo = PromptRepository(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_split_full_name(self):
        owner, repo = _split_full_name("octocat/hello-world")
        self.assertEqual(owner, "octocat")
        self.assertEqual(repo, "hello-world")

        with self.assertRaises(ValueError):
            _split_full_name("invalid-name-without-slash")

        with self.assertRaises(ValueError):
            _split_full_name("/missing-owner")

        with self.assertRaises(ValueError):
            _split_full_name("missing-repo/")

    def test_validate_github_config(self):
        # Valid
        self.assertIsNone(validate_github_config("user/repo", "main", "prompts.json"))

        # Invalid repo
        self.assertIsNotNone(validate_github_config("invalid", "main", "prompts.json"))

        # Empty branch
        self.assertIsNotNone(validate_github_config("user/repo", "", "prompts.json"))

        # Path traversal
        self.assertIsNotNone(validate_github_config("user/repo", "main", "../secret.json"))
        self.assertIsNotNone(validate_github_config("user/repo", "main", "/absolute/path.json"))

    def test_build_authenticated_remote_url(self):
        url = build_authenticated_remote_url("owner/repo", "ghp_1234567890")
        self.assertEqual(url, "https://oauth2:ghp_1234567890@github.com/owner/repo.git")

    def test_github_client_empty_token_raises(self):
        with self.assertRaises(ValueError):
            GithubClient("")
        with self.assertRaises(ValueError):
            GithubClient("   ")

    def test_push_library_via_api_mocked(self):
        mock_client = MagicMock(spec=GithubClient)
        mock_client.create_or_update_file.return_value = {
            "content": {"name": "prompt-library.json", "sha": "abc1234"},
            "commit": {"sha": "c0ffee1234567890"},
        }

        res = push_library_via_api(
            self.repo,
            mock_client,
            "testowner/prompt-library",
            branch="main",
            file_path="prompt-library.json",
        )
        self.assertIn("commit", res)
        mock_client.create_or_update_file.assert_called_once()
        call_kwargs = mock_client.create_or_update_file.call_args[1]
        self.assertEqual(call_kwargs["full_name"], "testowner/prompt-library")
        self.assertEqual(call_kwargs["branch"], "main")
        self.assertEqual(call_kwargs["path"], "prompt-library.json")

        # Verify exported json has valid content
        content_sent = json.loads(call_kwargs["content_str"])
        self.assertIn("prompts", content_sent)

    def test_pull_library_via_api_mocked(self):
        mock_client = MagicMock(spec=GithubClient)
        sample_library = {
            "version": "1.1",
            "folders": [],
            "tags": [],
            "templates": [],
            "prompts": [
                {
                    "id": "pulled-p1",
                    "title": "Pulled Prompt",
                    "template_content": "Hello from GitHub!",
                    "target_model": "General",
                    "temperature": 0.7,
                    "is_favorite": False,
                    "use_count": 0,
                    "tags": [],
                    "created_at": "2026-08-28T00:00:00",
                    "updated_at": "2026-08-28T00:00:00",
                }
            ],
        }
        b64_content = base64.b64encode(json.dumps(sample_library).encode("utf-8")).decode("ascii")
        mock_client.get_file.return_value = {
            "name": "prompt-library.json",
            "sha": "fedcba987",
            "content": b64_content,
        }

        count, info = pull_library_via_api(
            self.repo,
            mock_client,
            "testowner/prompt-library",
            branch="main",
            file_path="prompt-library.json",
        )
        self.assertEqual(count, 1)
        self.assertEqual(info["sha"], "fedcba987")

        # Check prompt now in local repo
        p = self.repo.get_prompt_by_id("pulled-p1")
        self.assertIsNotNone(p)
        self.assertEqual(p.title, "Pulled Prompt")
        self.assertEqual(p.template_content, "Hello from GitHub!")

    def test_pull_library_404_raises(self):
        mock_client = MagicMock(spec=GithubClient)
        mock_client.get_file.return_value = None

        with self.assertRaises(GithubError):
            pull_library_via_api(
                self.repo,
                mock_client,
                "testowner/prompt-library",
                branch="main",
                file_path="nonexistent.json",
            )

    def test_push_individual_prompts_via_api(self):
        mock_client = MagicMock(spec=GithubClient)
        count = push_individual_prompts_via_api(
            self.repo,
            mock_client,
            "testowner/prompt-library",
            branch="main",
            folder="prompts",
        )
        self.assertGreaterEqual(count, 1)
        self.assertEqual(mock_client.create_or_update_file.call_count, count)


if __name__ == "__main__":
    unittest.main()
