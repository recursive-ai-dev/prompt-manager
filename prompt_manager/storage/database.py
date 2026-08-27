"""Database connection, schema management, and migrations for Prompt Manager."""

from pathlib import Path
import sqlite3
import uuid
from typing import Optional
from prompt_manager.config import DATABASE_PATH, ensure_directories

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS folders (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id TEXT REFERENCES folders(id) ON DELETE CASCADE,
    icon TEXT DEFAULT 'folder',
    sort_order INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompts (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    folder_id TEXT REFERENCES folders(id) ON DELETE SET NULL,
    template_content TEXT NOT NULL,
    system_instruction TEXT DEFAULT '',
    target_model TEXT DEFAULT 'General',
    temperature REAL DEFAULT 0.7,
    is_favorite INTEGER DEFAULT 0,
    use_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    color TEXT DEFAULT '#3b82f6'
);

CREATE TABLE IF NOT EXISTS prompt_tags (
    prompt_id TEXT NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (prompt_id, tag_id)
);

CREATE TABLE IF NOT EXISTS prompt_revisions (
    id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    revision_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    template_content TEXT NOT NULL,
    system_instruction TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

-- Full-text search virtual table using FTS5
CREATE VIRTUAL TABLE IF NOT EXISTS prompts_fts USING fts5(
    id UNINDEXED,
    title,
    description,
    template_content,
    system_instruction
);

-- Triggers to maintain FTS index synchronized with prompts table
CREATE TRIGGER IF NOT EXISTS prompts_ai AFTER INSERT ON prompts BEGIN
    INSERT INTO prompts_fts(id, title, description, template_content, system_instruction)
    VALUES (new.id, new.title, new.description, new.template_content, new.system_instruction);
END;

CREATE TRIGGER IF NOT EXISTS prompts_ad AFTER DELETE ON prompts BEGIN
    DELETE FROM prompts_fts WHERE id = old.id;
END;

CREATE TRIGGER IF NOT EXISTS prompts_au AFTER UPDATE ON prompts BEGIN
    DELETE FROM prompts_fts WHERE id = old.id;
    INSERT INTO prompts_fts(id, title, description, template_content, system_instruction)
    VALUES (new.id, new.title, new.description, new.template_content, new.system_instruction);
END;
"""

STARTER_DATA = [
    {
        "folder": "Coding & Architecture",
        "prompts": [
            {
                "title": "Code Refactoring & Diagnostic",
                "description": "Deeply analyzes a code snippet for anti-patterns, memory leaks, and performance bottlenecks.",
                "system_instruction": "You are a Principal Software Architect. Be concise, mathematically rigorous, and explain the mechanical sympathy behind your recommendations.",
                "template_content": "Please review and refactor the following {{language:Python}} code snippet:\n\n```{{language}}\n{{code_snippet|multiline}}\n```\n\nFocus on: {{focus_areas:Performance & Memory|options:Performance & Memory,Readability & Clean Code,Security & Edge Cases}}\n\nProvide:\n1. Root cause diagnosis of existing issues\n2. Refactored production-ready implementation\n3. Benchmark or complexity analysis",
                "target_model": "Claude 3.7 Sonnet",
                "tags": ["coding", "refactoring", "performance"],
            },
            {
                "title": "Unit & Integration Test Suite Generator",
                "description": "Generates edge-case-heavy test suites with mocks and assertions.",
                "system_instruction": "You are an expert QA and Test Automation Engineer. Generate comprehensive, hermetic tests.",
                "template_content": "Generate a complete test suite for the following {{framework:pytest|options:pytest,unittest,jest,vitest,cargo-test}} code.\n\nCode under test:\n```{{language:python}}\n{{source_code|multiline}}\n```\n\nRequirements:\n- Achieve maximum edge case coverage\n- Include parameterized test cases where applicable\n- Mock external I/O and network boundaries\n- Target test runner: {{framework}}",
                "target_model": "GPT-4o",
                "tags": ["testing", "qa", "coding"],
            },
        ],
    },
    {
        "folder": "Writing & Summarization",
        "prompts": [
            {
                "title": "Executive Summary & Action Plan",
                "description": "Synthesizes complex notes, transcripts, or specifications into a 1-page executive brief.",
                "system_instruction": "You are an executive chief of staff. Deliver high-signal, zero-fluff syntheses tailored for rapid decision-making.",
                "template_content": "Summarize the following document into an Executive Brief for {{target_audience:VP & Leadership}}:\n\n---\n{{document_content|multiline}}\n---\n\nFormat requirements:\n1. Core Takeaway (2 sentences)\n2. Key Decisions & Rationales (bullet points)\n3. Critical Blockers & Risks\n4. Recommended Next Actions with Owners and Deadlines",
                "target_model": "Gemini 2.5 Pro",
                "tags": ["executive", "writing", "summary"],
            }
        ],
    },
]


class Database:
    """SQLite Database manager for Prompt Manager."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            ensure_directories()
            self.db_path = DATABASE_PATH
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self) -> None:
        """Initialize database schema and seed default prompts if empty."""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)

            # Check if any prompt exists
            cursor = conn.execute("SELECT COUNT(*) FROM prompts")
            count = cursor.fetchone()[0]
            if count == 0:
                self._seed_default_data(conn)

    def _seed_default_data(self, conn: sqlite3.Connection) -> None:
        """Seed starter categories, tags, and prompts."""
        for item in STARTER_DATA:
            folder_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO folders (id, name, created_at) VALUES (?, ?, datetime('now'))",
                (folder_id, item["folder"]),
            )

            for p in item["prompts"]:
                prompt_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO prompts (
                        id, title, description, folder_id, template_content,
                        system_instruction, target_model, is_favorite, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))
                    """,
                    (
                        prompt_id,
                        p["title"],
                        p["description"],
                        folder_id,
                        p["template_content"],
                        p["system_instruction"],
                        p["target_model"],
                    ),
                )

                # Seed tags
                for tag_name in p["tags"]:
                    tag_id = str(uuid.uuid4())
                    conn.execute(
                        "INSERT OR IGNORE INTO tags (id, name) VALUES (?, ?)",
                        (tag_id, tag_name),
                    )
                    # Fetch actual tag id if ignored
                    cur = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                    row = cur.fetchone()
                    if row:
                        actual_tag_id = row[0]
                        conn.execute(
                            "INSERT OR IGNORE INTO prompt_tags (prompt_id, tag_id) VALUES (?, ?)",
                            (prompt_id, actual_tag_id),
                        )
