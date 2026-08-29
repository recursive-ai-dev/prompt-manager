"""Export formatters for prompts into LLM API structures, frameworks, CSV, and portable files."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import uuid

from prompt_manager.core.models import Prompt


def to_plain_text(prompt: Prompt, hydrated_content: str = "") -> str:
    """Format prompt into plain text, incorporating system instruction if present."""
    content = hydrated_content if hydrated_content else prompt.template_content
    if prompt.system_instruction.strip():
        return f"[SYSTEM INSTRUCTION]\n{prompt.system_instruction.strip()}\n\n[USER PROMPT]\n{content.strip()}"
    return content.strip()


def to_openai_payload(prompt: Prompt, hydrated_content: str = "") -> Dict[str, Any]:
    """Format prompt into OpenAI-compatible Chat Completion JSON payload."""
    content = hydrated_content if hydrated_content else prompt.template_content
    messages = []

    if prompt.system_instruction.strip():
        messages.append({"role": "system", "content": prompt.system_instruction.strip()})

    messages.append({"role": "user", "content": content.strip()})

    payload: Dict[str, Any] = {
        "model": prompt.target_model if prompt.target_model != "General" else "gpt-4o",
        "messages": messages,
        "temperature": prompt.temperature,
    }
    return payload


def to_anthropic_payload(prompt: Prompt, hydrated_content: str = "") -> Dict[str, Any]:
    """Format prompt into Anthropic Messages API JSON payload."""
    content = hydrated_content if hydrated_content else prompt.template_content
    payload: Dict[str, Any] = {
        "model": (
            prompt.target_model
            if "claude" in prompt.target_model.lower()
            else "claude-3-7-sonnet-20250219"
        ),
        "messages": [{"role": "user", "content": content.strip()}],
        "temperature": prompt.temperature,
    }
    if prompt.system_instruction.strip():
        payload["system"] = prompt.system_instruction.strip()

    return payload


def to_markdown_frontmatter(prompt: Prompt, hydrated_content: str = "") -> str:
    """Format prompt as Markdown with YAML frontmatter."""
    tags_str = ", ".join(prompt.tags)
    content = hydrated_content if hydrated_content else prompt.template_content

    lines = [
        "---",
        f"title: {json.dumps(prompt.title)}",
        f"target_model: {json.dumps(prompt.target_model)}",
        f"temperature: {prompt.temperature}",
        f"tags: [{tags_str}]",
        f"created_at: {prompt.created_at}",
        f"updated_at: {prompt.updated_at}",
        "---",
        "",
    ]

    if prompt.description.strip():
        lines.extend([f"> {prompt.description.strip()}", ""])

    if prompt.system_instruction.strip():
        lines.extend([
            "## System Instruction",
            "",
            prompt.system_instruction.strip(),
            "",
        ])

    lines.extend([
        "## Prompt",
        "",
        content.strip(),
        "",
    ])

    return "\n".join(lines)


def to_langchain_template(prompt: Prompt) -> str:
    """Generate ready-to-run LangChain Python code snippet."""
    # Convert Mustache {{var}} or {{var:default}} to LangChain {var}
    clean_template = re.sub(r"\{\{([a-zA-Z0-9_]+)(?::[^|}]*)?(?:\|[^}]*)?\}\}", r"{\1}", prompt.template_content)
    clean_system = re.sub(r"\{\{([a-zA-Z0-9_]+)(?::[^|}]*)?(?:\|[^}]*)?\}\}", r"{\1}", prompt.system_instruction)

    code = [
        "# LangChain Prompt Template",
        "from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate",
        "",
        "messages = []",
    ]

    if clean_system.strip():
        code.extend([
            f'system_template = """{clean_system.strip()}"""',
            "messages.append(SystemMessagePromptTemplate.from_template(system_template))",
        ])

    code.extend([
        f'human_template = """{clean_template.strip()}"""',
        "messages.append(HumanMessagePromptTemplate.from_template(human_template))",
        "",
        "prompt = ChatPromptTemplate.from_messages(messages)",
        "# chain = prompt | llm | StrOutputParser()",
    ])

    return "\n".join(code)


def to_llamaindex_template(prompt: Prompt) -> str:
    """Generate ready-to-run LlamaIndex Python code snippet."""
    clean_template = re.sub(r"\{\{([a-zA-Z0-9_]+)(?::[^|}]*)?(?:\|[^}]*)?\}\}", r"{\1}", prompt.template_content)

    return f'''# LlamaIndex Prompt Template
from llama_index.core import PromptTemplate

template_str = """{clean_template.strip()}"""
prompt_tmpl = PromptTemplate(template_str)
'''


def to_csv_string(prompts: List[Prompt]) -> str:
    """Export list of prompts as a standard CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "title",
        "description",
        "template_content",
        "system_instruction",
        "target_model",
        "temperature",
        "tags",
        "is_favorite",
        "created_at",
        "updated_at",
    ])

    for p in prompts:
        writer.writerow([
            p.id,
            p.title,
            p.description,
            p.template_content,
            p.system_instruction,
            p.target_model,
            p.temperature,
            ";".join(p.tags),
            1 if p.is_favorite else 0,
            p.created_at,
            p.updated_at,
        ])

    return output.getvalue()


def from_csv_string(csv_text: str) -> List[Prompt]:
    """Parse CSV text back into Prompt objects."""
    reader = csv.DictReader(io.StringIO(csv_text))
    prompts: List[Prompt] = []

    for row in reader:
        tags_raw = row.get("tags", "")
        tags = [t.strip() for t in tags_raw.split(";") if t.strip()] if tags_raw else []
        p = Prompt(
            id=row.get("id") or str(uuid.uuid4()),
            title=row.get("title", "Untitled Prompt"),
            description=row.get("description", ""),
            template_content=row.get("template_content", ""),
            system_instruction=row.get("system_instruction", ""),
            target_model=row.get("target_model", "General"),
            temperature=float(row.get("temperature", 0.7)),
            is_favorite=bool(int(row.get("is_favorite", 0))),
            tags=tags,
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )
        prompts.append(p)

    return prompts


def format_json_string(obj: Any) -> str:
    """Convert payload dictionary to nicely formatted JSON."""
    return json.dumps(obj, indent=2, ensure_ascii=False)
