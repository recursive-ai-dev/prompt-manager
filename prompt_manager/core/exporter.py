"""Export formatters for prompts into LLM API structures and portable files."""

import json
from typing import Any, Dict
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


def format_json_string(obj: Any) -> str:
    """Convert payload dictionary to nicely formatted JSON."""
    return json.dumps(obj, indent=2, ensure_ascii=False)
