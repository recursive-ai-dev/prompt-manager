"""Import and export entire prompt library to JSON."""

import json
from pathlib import Path
from typing import Any, Dict
from prompt_manager.core.models import Folder, Prompt, PromptTemplate, Tag
from prompt_manager.storage.repository import PromptRepository


def export_library_to_json(repo: PromptRepository, filepath: Path) -> int:
    """Export all prompts, folders, tags, and prompt_templates to a portable JSON file."""
    folders = repo.list_folders()
    tags = repo.list_tags()
    prompts = repo.list_prompts()
    # Templates are infrastructure only — may be empty; included for completeness
    try:
        templates = repo.list_templates()
    except Exception:
        templates = []

    data: Dict[str, Any] = {
        "version": "1.1",
        "folders": [
            {
                "id": f.id,
                "name": f.name,
                "parent_id": f.parent_id,
                "icon": f.icon,
                "sort_order": f.sort_order,
                "created_at": f.created_at,
            }
            for f in folders
        ],
        "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in tags],
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "content": t.content,
                "system_instruction": t.system_instruction,
                "category": t.category,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            }
            for t in templates
        ],
        "prompts": [
            {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "folder_id": p.folder_id,
                "template_id": p.template_id,
                "template_content": p.template_content,
                "system_instruction": p.system_instruction,
                "target_model": p.target_model,
                "temperature": p.temperature,
                "is_favorite": p.is_favorite,
                "use_count": p.use_count,
                "tags": p.tags,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }
            for p in prompts
        ],
    }

    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(prompts)


def import_library_from_json(repo: PromptRepository, filepath: Path) -> int:
    """Import prompts, folders, tags, and prompt_templates from a JSON backup file."""
    content = filepath.read_text(encoding="utf-8")
    data = json.loads(content)

    for f_data in data.get("folders", []):
        repo.save_folder(
            Folder(
                id=f_data["id"],
                name=f_data["name"],
                parent_id=f_data.get("parent_id"),
                icon=f_data.get("icon", "folder"),
                sort_order=f_data.get("sort_order", 0),
                created_at=f_data.get("created_at", ""),
            )
        )

    for t_data in data.get("tags", []):
        repo.save_tag(
            Tag(
                id=t_data["id"],
                name=t_data["name"],
                color=t_data.get("color", "#3b82f6"),
            )
        )

    # Import templates first (prompts may reference template_id)
    for tmpl_data in data.get("templates", []):
        try:
            repo.save_template(
                PromptTemplate(
                    id=tmpl_data["id"],
                    name=tmpl_data.get("name", "Untitled Template"),
                    description=tmpl_data.get("description", ""),
                    content=tmpl_data.get("content", ""),
                    system_instruction=tmpl_data.get("system_instruction", ""),
                    category=tmpl_data.get("category", "general"),
                    created_at=tmpl_data.get("created_at", ""),
                    updated_at=tmpl_data.get("updated_at", ""),
                )
            )
        except Exception:
            # Skip invalid templates but continue import (e.g., duplicate name)
            continue

    imported_count = 0
    for p_data in data.get("prompts", []):
        p = Prompt(
            id=p_data["id"],
            title=p_data.get("title", "Imported Prompt"),
            description=p_data.get("description", ""),
            folder_id=p_data.get("folder_id"),
            template_id=p_data.get("template_id"),
            template_content=p_data.get("template_content", ""),
            system_instruction=p_data.get("system_instruction", ""),
            target_model=p_data.get("target_model", "General"),
            temperature=float(p_data.get("temperature", 0.7)),
            is_favorite=bool(p_data.get("is_favorite", False)),
            use_count=int(p_data.get("use_count", 0)),
            tags=p_data.get("tags", []),
            created_at=p_data.get("created_at", ""),
            updated_at=p_data.get("updated_at", ""),
        )
        repo.save_prompt(p)
        imported_count += 1

    return imported_count
