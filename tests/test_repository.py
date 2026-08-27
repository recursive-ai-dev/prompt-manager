import tempfile
from pathlib import Path
import unittest

from prompt_manager.core.models import Folder, Prompt, Tag
from prompt_manager.storage.database import Database
from prompt_manager.storage.repository import PromptRepository


class TestRepository(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db = Database(self.db_path)
        self.repo = PromptRepository(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_starter_data_seeded(self):
        prompts = self.repo.list_prompts()
        self.assertGreater(len(prompts), 0)
        folders = self.repo.list_folders()
        self.assertGreater(len(folders), 0)

    def test_create_and_read_prompt(self):
        prompt = Prompt(
            title="Custom Test Prompt",
            description="A test description",
            template_content="Hello {{world}}",
            system_instruction="You are a test helper",
            tags=["test", "custom"],
        )
        saved = self.repo.save_prompt(prompt)
        self.assertEqual(saved.id, prompt.id)

        fetched = self.repo.get_prompt_by_id(prompt.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, "Custom Test Prompt")
        self.assertEqual(fetched.tags, ["custom", "test"])

    def test_full_text_search(self):
        prompt = Prompt(
            title="Kubernetes Helm Deployment Helper",
            description="Generates helm chart templates",
            template_content="Deploy {{service_name}} to cluster",
        )
        self.repo.save_prompt(prompt)

        results = self.repo.list_prompts(search_query="Kubernetes")
        self.assertTrue(any(p.title == "Kubernetes Helm Deployment Helper" for p in results))

        results_by_body = self.repo.list_prompts(search_query="cluster")
        self.assertTrue(any(p.title == "Kubernetes Helm Deployment Helper" for p in results_by_body))

    def test_revisions(self):
        prompt = Prompt(
            title="Versioned Prompt",
            template_content="Initial Version",
        )
        self.repo.save_prompt(prompt)

        prompt.template_content = "Updated Version 2"
        self.repo.save_prompt(prompt, create_revision=True)

        revisions = self.repo.get_revisions(prompt.id)
        self.assertEqual(len(revisions), 1)
        self.assertEqual(revisions[0].template_content, "Updated Version 2")


if __name__ == "__main__":
    unittest.main()
