"""Repository abstraction for Prompt Manager persistence operations."""

from datetime import datetime
import re
import sqlite3
from typing import List, Optional
import uuid

from prompt_manager.core.models import Folder, Prompt, PromptRevision, Tag
from prompt_manager.storage.database import Database


class PromptRepository:
    """Handles CRUD, querying, search, and revision history for prompts."""

    def __init__(self, db: Database):
        self.db = db

    def get_prompt_by_id(self, prompt_id: str) -> Optional[Prompt]:
        with self.db.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, title, description, folder_id, template_content,
                       system_instruction, target_model, temperature, is_favorite,
                       use_count, created_at, updated_at
                FROM prompts WHERE id = ?
                """,
                (prompt_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            tags = self._get_tags_for_prompt(conn, prompt_id)
            return Prompt(
                id=row["id"],
                title=row["title"],
                description=row["description"] or "",
                folder_id=row["folder_id"],
                template_content=row["template_content"],
                system_instruction=row["system_instruction"] or "",
                target_model=row["target_model"],
                temperature=row["temperature"],
                is_favorite=bool(row["is_favorite"]),
                use_count=row["use_count"],
                tags=tags,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def list_prompts(
        self,
        folder_id: Optional[str] = None,
        tag_id: Optional[str] = None,
        favorite_only: bool = False,
        search_query: Optional[str] = None,
    ) -> List[Prompt]:
        """Fetch prompts filtered by folder, tag, favorite, or FTS query."""
        with self.db.get_connection() as conn:
            params = []
            conditions = []

            if favorite_only:
                conditions.append("p.is_favorite = 1")

            if folder_id:
                conditions.append("p.folder_id = ?")
                params.append(folder_id)

            if tag_id:
                conditions.append(
                    "p.id IN (SELECT prompt_id FROM prompt_tags WHERE tag_id = ?)"
                )
                params.append(tag_id)

            if search_query and search_query.strip():
                clean_query = self._sanitize_fts_query(search_query)
                if clean_query:
                    conditions.append(
                        "p.id IN (SELECT id FROM prompts_fts WHERE prompts_fts MATCH ?)"
                    )
                    params.append(clean_query)
                else:
                    # Fallback to LIKE if query was purely punctuation
                    conditions.append(
                        "(p.title LIKE ? OR p.template_content LIKE ? OR p.description LIKE ?)"
                    )
                    like_term = f"%{search_query.strip()}%"
                    params.extend([like_term, like_term, like_term])

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            sql = f"""
                SELECT p.id, p.title, p.description, p.folder_id, p.template_content,
                       p.system_instruction, p.target_model, p.temperature, p.is_favorite,
                       p.use_count, p.created_at, p.updated_at
                FROM prompts p
                {where_clause}
                ORDER BY p.is_favorite DESC, p.updated_at DESC
            """

            cur = conn.execute(sql, params)
            prompts = []
            for row in cur.fetchall():
                prompt_id = row["id"]
                tags = self._get_tags_for_prompt(conn, prompt_id)
                prompts.append(
                    Prompt(
                        id=prompt_id,
                        title=row["title"],
                        description=row["description"] or "",
                        folder_id=row["folder_id"],
                        template_content=row["template_content"],
                        system_instruction=row["system_instruction"] or "",
                        target_model=row["target_model"],
                        temperature=row["temperature"],
                        is_favorite=bool(row["is_favorite"]),
                        use_count=row["use_count"],
                        tags=tags,
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            return prompts

    def save_prompt(self, prompt: Prompt, create_revision: bool = False) -> Prompt:
        """Create or update a prompt, updating tags and optionally creating a revision."""
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            # Check if prompt exists
            cur = conn.execute("SELECT id FROM prompts WHERE id = ?", (prompt.id,))
            exists = cur.fetchone() is not None

            if exists:
                conn.execute(
                    """
                    UPDATE prompts SET
                        title = ?, description = ?, folder_id = ?, template_content = ?,
                        system_instruction = ?, target_model = ?, temperature = ?,
                        is_favorite = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        prompt.title,
                        prompt.description,
                        prompt.folder_id,
                        prompt.template_content,
                        prompt.system_instruction,
                        prompt.target_model,
                        prompt.temperature,
                        1 if prompt.is_favorite else 0,
                        now,
                        prompt.id,
                    ),
                )
                prompt.updated_at = now
            else:
                prompt.created_at = now
                prompt.updated_at = now
                conn.execute(
                    """
                    INSERT INTO prompts (
                        id, title, description, folder_id, template_content,
                        system_instruction, target_model, temperature, is_favorite,
                        use_count, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prompt.id,
                        prompt.title,
                        prompt.description,
                        prompt.folder_id,
                        prompt.template_content,
                        prompt.system_instruction,
                        prompt.target_model,
                        prompt.temperature,
                        1 if prompt.is_favorite else 0,
                        prompt.use_count,
                        prompt.created_at,
                        prompt.updated_at,
                    ),
                )

            # Update tags
            conn.execute("DELETE FROM prompt_tags WHERE prompt_id = ?", (prompt.id,))
            for tag_name in prompt.tags:
                clean_tag = tag_name.strip().lstrip("#").lower()
                if not clean_tag:
                    continue
                tag_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT OR IGNORE INTO tags (id, name) VALUES (?, ?)",
                    (tag_id, clean_tag),
                )
                cur = conn.execute("SELECT id FROM tags WHERE name = ?", (clean_tag,))
                tag_row = cur.fetchone()
                if tag_row:
                    conn.execute(
                        "INSERT OR IGNORE INTO prompt_tags (prompt_id, tag_id) VALUES (?, ?)",
                        (prompt.id, tag_row[0]),
                    )

            if create_revision and exists:
                self._record_revision(conn, prompt)

        return prompt

    def delete_prompt(self, prompt_id: str) -> bool:
        with self.db.get_connection() as conn:
            cur = conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
            return cur.rowcount > 0

    def toggle_favorite(self, prompt_id: str) -> bool:
        with self.db.get_connection() as conn:
            cur = conn.execute(
                "SELECT is_favorite FROM prompts WHERE id = ?", (prompt_id,)
            )
            row = cur.fetchone()
            if not row:
                return False
            new_fav = 0 if row["is_favorite"] else 1
            conn.execute(
                "UPDATE prompts SET is_favorite = ? WHERE id = ?", (new_fav, prompt_id)
            )
            return bool(new_fav)

    def increment_use_count(self, prompt_id: str) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE prompts SET use_count = use_count + 1 WHERE id = ?",
                (prompt_id,),
            )

    # ------------------ Folders ------------------

    def list_folders(self) -> List[Folder]:
        with self.db.get_connection() as conn:
            cur = conn.execute(
                "SELECT id, name, parent_id, icon, sort_order, created_at FROM folders ORDER BY sort_order, name ASC"
            )
            return [
                Folder(
                    id=row["id"],
                    name=row["name"],
                    parent_id=row["parent_id"],
                    icon=row["icon"],
                    sort_order=row["sort_order"],
                    created_at=row["created_at"],
                )
                for row in cur.fetchall()
            ]

    def save_folder(self, folder: Folder) -> Folder:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO folders (id, name, parent_id, icon, sort_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    parent_id=excluded.parent_id,
                    icon=excluded.icon,
                    sort_order=excluded.sort_order
                """,
                (
                    folder.id,
                    folder.name,
                    folder.parent_id,
                    folder.icon,
                    folder.sort_order,
                    folder.created_at,
                ),
            )
        return folder

    def delete_folder(self, folder_id: str) -> bool:
        with self.db.get_connection() as conn:
            cur = conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
            return cur.rowcount > 0

    # ------------------ Tags ------------------

    def list_tags(self) -> List[Tag]:
        with self.db.get_connection() as conn:
            cur = conn.execute("SELECT id, name, color FROM tags ORDER BY name ASC")
            return [
                Tag(id=row["id"], name=row["name"], color=row["color"])
                for row in cur.fetchall()
            ]

    def save_tag(self, tag: Tag) -> Tag:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tags (id, name, color)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name, color=excluded.color
                """,
                (tag.id, tag.name, tag.color),
            )
        return tag

    def delete_tag(self, tag_id: str) -> bool:
        with self.db.get_connection() as conn:
            cur = conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
            return cur.rowcount > 0

    # ------------------ Revisions ------------------

    def get_revisions(self, prompt_id: str) -> List[PromptRevision]:
        with self.db.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, prompt_id, revision_number, title, template_content,
                       system_instruction, created_at
                FROM prompt_revisions
                WHERE prompt_id = ?
                ORDER BY revision_number DESC
                """,
                (prompt_id,),
            )
            return [
                PromptRevision(
                    id=row["id"],
                    prompt_id=row["prompt_id"],
                    revision_number=row["revision_number"],
                    title=row["title"],
                    template_content=row["template_content"],
                    system_instruction=row["system_instruction"] or "",
                    created_at=row["created_at"],
                )
                for row in cur.fetchall()
            ]

    def _record_revision(self, conn: sqlite3.Connection, prompt: Prompt) -> None:
        cur = conn.execute(
            "SELECT COALESCE(MAX(revision_number), 0) + 1 FROM prompt_revisions WHERE prompt_id = ?",
            (prompt.id,),
        )
        next_rev = cur.fetchone()[0]
        conn.execute(
            """
            INSERT INTO prompt_revisions (
                id, prompt_id, revision_number, title, template_content,
                system_instruction, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                str(uuid.uuid4()),
                prompt.id,
                next_rev,
                prompt.title,
                prompt.template_content,
                prompt.system_instruction,
            ),
        )

    # ------------------ Helpers ------------------

    def _get_tags_for_prompt(self, conn: sqlite3.Connection, prompt_id: str) -> List[str]:
        cur = conn.execute(
            """
            SELECT t.name FROM tags t
            JOIN prompt_tags pt ON pt.tag_id = t.id
            WHERE pt.prompt_id = ?
            ORDER BY t.name ASC
            """,
            (prompt_id,),
        )
        return [r[0] for r in cur.fetchall()]

    def _sanitize_fts_query(self, query: str) -> str:
        """Escape and format a search query for SQLite FTS5 prefix token matching."""
        tokens = re.findall(r"\w+", query)
        if not tokens:
            return ""
        # Match tokens as prefixes for responsive instant search: e.g. "code ref*"
        formatted = " ".join([f'"{token}"*' for token in tokens])
        return formatted
