"""Import and export entire prompt library to JSON."""

import json
from pathlib import Path
from typing import Any, Dict
from prompt_manager.core.models import Folder, Prompt, Tag
from prompt_manager.storage.repository import PromptRepository


def export_library_to_json(repo: PromptRepository, filepath: Path) -> int:
    """Export all prompts, folders, and tags to a portable JSON file."""
    folders = repo.list_folders()
    tags = repo.list_tags()
    prompts = repo.list_prompts()

    data: Dict[str, Any] = {
        "version": "1.0",
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
        "prompts": [
            {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "folder_id": p.folder_id,
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
    """Import prompts, folders, and tags from a JSON backup file."""
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

    imported_count = 0
    for p_data in data.get("prompts", []):
        p = Prompt(
            id=p_data["id"],
            title=p_data.get("title", "Imported Prompt"),
            description=p_data.get("description", ""),
            folder_id=p_data.get("folder_id"),
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
