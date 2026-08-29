"""Data models for Prompt Manager."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid


@dataclass
class VariableSpec:
    """Specification for a template variable detected in prompt text."""
    name: str
    default_value: str = ""
    is_multiline: bool = False
    options: List[str] = field(default_factory=list)

    @property
    def has_options(self) -> bool:
        return len(self.options) > 0


@dataclass
class Folder:
    """Hierarchical folder for prompt organization."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    parent_id: Optional[str] = None
    icon: str = "folder"
    sort_order: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Tag:
    """Tag with color coding for multi-dimensional filtering."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    color: str = "#3b82f6"


@dataclass
class PromptRevision:
    """Snapshot revision of a prompt's historical state."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt_id: str = ""
    revision_number: int = 1
    title: str = ""
    template_content: str = ""
    system_instruction: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PromptTemplate:
    """Reusable template definition for creating prompts.

    Infrastructure only — no default templates are seeded.
    Users can create arbitrary templates (e.g. 'code-review', 'summarization',
    'chat', 'tool-use') and instantiate Prompts from them via `template_id`.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    content: str = ""
    system_instruction: str = ""
    category: str = "general"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def variable_specs(self) -> List["VariableSpec"]:
        """Derive VariableSpecs from content + system_instruction."""
        from prompt_manager.core.template_engine import extract_variables

        combined = f"{self.content}\n{self.system_instruction}"
        return extract_variables(combined)


@dataclass
class Prompt:
    """Core Prompt entity."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "Untitled Prompt"
    description: str = ""
    folder_id: Optional[str] = None
    template_content: str = ""
    system_instruction: str = ""
    target_model: str = "General"
    temperature: float = 0.7
    is_favorite: bool = False
    use_count: int = 0
    tags: List[str] = field(default_factory=list)
    # Optional link to a PromptTemplate this prompt was instantiated from
    template_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
