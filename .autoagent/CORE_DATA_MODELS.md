# CORE DATA MODELS - Field Mapping, Ownership & Invariants

> Status: PRE-RECORD (mapping complete, implementation pending).
> Goal: harden prompt_manager/core/models.py - Prompt, Folder, Tag,
> PromptRevision, PromptTemplate, VariableSpec - and invariants every
> other layer (storage, exporters, UI) relies on.
> Loop: Field Mapping -> Pre-record -> Implementation -> Record.

Sources: core/models.py (97 lines, 6 dataclasses, zero validation),
storage/database.py SCHEMA_SQL, storage/repository.py, storage/backup.py,
core/exporter.py, core/template_engine.py, ui/components/editor.py,
ui/main_window.py, ui/components/template_manager.py, sidebar.py.

## 1. Construction / mutation / serialization / persistence map

| Model | Constructed at | Mutated at | Serialized at | Persisted at |
|---|---|---|---|---|
| Prompt | repository.get_prompt_by_id, list_prompts (rows+_get_tags_for_prompt), create_prompt_from_template, backup.import_library_from_json, exporter.from_csv_string, ui/main_window._on_new_prompt + _on_duplicate_prompt, tests | editor.update_prompt_model (title/desc/model/temp/folder/tags/system/content), repository.save_prompt (stamps updated_at on update, created_at/updated_at on insert if falsy), toggle_favorite + increment_use_count (raw SQL, bypass model) | backup.export_library_to_json (all fields), exporter.to_csv_string (SUBSET - drops folder_id/template_id/use_count), to_markdown_frontmatter (SUBSET - drops ids/favorite/count), to_openai/anthropic/langchain/llamaindex/plain | repository.save_prompt (INSERT/UPDATE prompts + DELETE+INSERT prompt_tags), database._seed_default_data (raw SQL) |
| Folder | repository.list_folders, backup.import_library_from_json, main_window._on_create_folder(Folder(name=...)), tests | main_window._on_rename_folder (.name), repository.save_folder (UPSERT, never touches timestamp) | backup.export_library_to_json (all fields) | save_folder/delete_folder, _seed_default_data |
| Tag | repository.list_tags, backup.import_library_from_json, UI never constructs Tag directly (editor uses raw strings), tests | repository.save_tag (UPSERT by id) | backup.export_library_to_json (id/name/color) | save_tag/delete_tag, prompt_tags join via save_prompt |
| PromptRevision | repository.get_revisions only | never mutated; _record_revision creates via raw SQL datetime(now) NOT via model | NEVER exported (not in JSON/CSV/Markdown) | prompt_revisions (CASCADE on prompt delete) |
| PromptTemplate | repository.get_template_by_id/name, list_templates, backup.import_library_from_json, template_manager._on_duplicate, main_window GitHub import, tests | template_manager.TemplateEditorWidget.update_model, repository.save_template (strips name, lowercases category, stamps updated_at) | backup.export_library_to_json (all fields) | save_template/delete_template |
| VariableSpec | template_engine.extract_variables only (regex VARIABLE_PATTERN), never by UI/storage | merged in-place in extract_variables (later occurrence upgrades default/multiline/options) | never persisted; rendered into variable_form widgets + template_manager hint | not persisted |

## 2. Field tables (type / default / owner) + ambiguities

### VariableSpec: name str required (engine regex [a-zA-Z0-9_-]+; model strips; AMBIG: direct VariableSpec(name="") succeeds - who rejects?); default_value str "" (model coerces None->""; AMBIG: None breaks hydrate); is_multiline bool False (model explicit coerce; AMBIG: bool("false")==True trap); options List[str] [] (model strips/filters/dedupes; AMBIG: None/""/[" a ","","a"] stored as-is today); has_options property OK.

### Folder: id str uuid4 (model ensures non-empty; DB PK; JSON preserves; CSV/Markdown drop; AMBIG: Folder(id="") violates PK); name str "" (UI+repo should reject empty; model coerces None->"" + strip; AMBIG: "" passes NOT NULL, no maxlen); parent_id Optional[str] None (model ""->None + strip; repo owns existence; AMBIG: orphan -> IntegrityError crash; self-parent/cycle undetected; ON DELETE CASCADE deletes children - undocumented in model); icon str "folder" (model empty->"folder"; AMBIG: no allowlist); sort_order int 0 (model int(float) fallback 0; backup _safe_int; AMBIG: "not_an_int"/None/float/negative); created_at str ISO8601 now().isoformat() (model ensures; repo preserves on UPSERT; AMBIG: NO updated_at on Folder; dual clocks: python isoformat local-naive-micro vs sqlite datetime(now) UTC-seconds; "" stored as-is today).

### Tag: id str uuid4 (same empty-id risk; JSON preserves; CSV/Markdown drop id); name str "" (model strip/lstrip(#)/lower; repo owns uniqueness; AMBIG: Prompt.tags stores NAMES, prompt_tags stores IDS, mapping in save_prompt name->id + _get_tags_for_prompt id->name ORDER BY name. But save_tag does NOT normalize while save_prompt lowercases -> duplicate case variants. save_tag UPSERTs by id not name -> duplicate name+different id raises IntegrityError crash. Empty names allowed); color str "#3b82f6" (model validates #RRGGBB fallback default; AMBIG: any string accepted today; color lost on Prompt round-trip - only names travel).

### PromptRevision: id str uuid4 (model+repo; AMBIG: _record_revision generates own uuid4 via SQL bypassing model - two id sources; new id per revision good; never exported); prompt_id str "" (repo owns FK; model strips; AMBIG: "" violates NOT NULL+FK if persisted via model); revision_number int 1 (repo owns MAX+1; model coerces >=1; AMBIG: default 1 never used; no UNIQUE(prompt_id, revision_number) so concurrent MAX+1 races; negative possible); title/template_content/system_instruction str (model coerces None->""); created_at str ISO8601 (repo owns via SQL datetime(now) UTC-seconds; model ensures format; AMBIG: format mismatch model-T-micro-local vs SQL-space-seconds-UTC; which layer sets them? BOTH, inconsistently).

### PromptTemplate: id str uuid4 (same empty risk; JSON preserves; CSV/Markdown drop); name str "" (repo owns non-empty+uniqueness ValueError; model strips; AMBIG: model allows ""; repo manual UNIQUE check race-prone but DB UNIQUE backs it); description str "" OK; content str "" (repo owns non-empty ValueError; same split); system_instruction str "" OK; category str "general" (repo normalizes strip.lower or general; model mirrors; AMBIG: UI CATEGORY_CHOICES 9 values but combo editable -> arbitrary strings; saved lowercased; list_templates(category="All") special-cased); created_at/updated_at str ISO8601 (model ensures; repo sets now on insert if falsy, overwrites updated_at on update; AMBIG: dual clocks; backup passes "" -> repo fills on insert since "" falsy, but save_folder does NOT fill); variable_specs() derived via extract_variables(content+"\\n"+system) (AMBIG SYNC RISK: models.variable_specs == template_manager._update_vars_hint concatenation, but main_window._on_editor_content_changed extracts from template_edit ONLY omitting system. Prompt has NO variable_specs() - callers reimplement. Engine regex change must propagate to all three).

### Prompt: id str uuid4 (model ensures; UI/repo preserve; JSON+CSV preserve; Markdown drops; AMBIG: from_csv_string uses or-uuid4 good, import_library_from_json uses p_data["id"] KeyError if missing. _on_duplicate_prompt mints new uuid4 good but drops template_id/is_favorite/use_count silently); title str "Untitled Prompt" (UI or-default + model empty->default; DB NOT NULL; AMBIG: whitespace stored; no maxlen); description str "" (AMBIG: None stores None); folder_id Optional None (model ""->None; repo owns existence nullify-orphan never-crash; DB ON DELETE SET NULL; AMBIG: orphan->IntegrityError crash today; CSV drops column entirely -> imports land in Root silent loss; Markdown drops; sidebar copy moved-to-Root matches SET NULL but undocumented); template_id Optional None (same as folder_id; create_prompt_from_template sets link; _on_duplicate_prompt drops silently; delete_template nullifies tested but undocumented); template_content str "" (NOT NULL OK); system_instruction str "" (reads use or-"" for NULL; AMBIG: writes may pass None); target_model str "General" (model empty->General; UI combo editable any string; AMBIG: config.DEFAULT_TARGET_MODELS 10 presets but free-text; exporters special-case General->gpt-4o and non-claude->default Anthropic - undocumented in model); temperature float 0.7 (model coerces+clamps 0.0-2.0 fallback 0.7; UI spin 0.0-2.0; backup/CSV _safe_float; AMBIG: no bounds in model/DB today; strings/None/NaN/-1/5 storable; bool is int subclass True->1.0 trap; silent fallback 0.7 better than crash but unlogged); is_favorite bool False (model explicit coerce false/0->False; DB 0/1; repo 1-if-else-0; AMBIG: bool("false") is True trap; CSV 0/1 via _safe_int; JSON bool; Markdown drops lossy; toggle_favorite bypasses model + doesnt touch updated_at); use_count int 0 (model coerces floor 0; repo increment_use_count owns increments; AMBIG: save_prompt UPDATE path OMITS use_count - discards in-memory changes silently, only increment persists; negative/float/string/None possible; CSV drops -> 0 on reimport; JSON preserves); tags List[str]-names [] (model strip/lstrip-#/lower/drop-empty/dedupe; repo resolves names<->ids + ORDER BY name on read; AMBIG: editor splits on comma no-lower, save_prompt lowercases - diverges until re-read; CSV ";".join vs Markdown/editor ", ".join - tags with ,/; ambiguous; color lives on Tag lost when only names travel; in-memory insertion order vs DB sorted order differ); created_at/updated_at str ISO8601 (model ensures; repo sets both on insert if falsy, overwrites updated_at on update; AMBIG: dual clocks; toggle_favorite/increment_use_count dont touch updated_at - is fav/use bump a modification? undocumented; CSV header has both but from_csv_string passes "" -> repo fills on insert good; JSON same).

## 3. Cross-cutting ambiguities (must resolve)

1. ID stability: revisions mint new ids (good) but folder/tag ids invisible in CSV/Markdown. Markdown filename uses id[:8] suffix - stable only if id in memory. Document: JSON=lossless (ids preserved), CSV=ids preserved for prompts only (folders/tags/templates lost), Markdown=lossy human export (no ids, no reimport).
2. Timestamps: two writers (python datetime.now().isoformat() local-naive-micro vs sqlite datetime(now) UTC-seconds). Readers accept both + "". Proposed: model _ensure_timestamp normalizes None/""/unparseable->now, datetime->isoformat, valid strings->normalized isoformat; repository remains owner stamping updated_at on write.
3. Orphans: folder_id/template_id/parent_id FKs + ON DELETE SET NULL/CASCADE in DDL, but save_prompt/save_folder never pre-check -> orphan insert crashes IntegrityError. Proposed: model ""->None; repository nullifies non-existent FK explicitly (never crash); document SET NULL vs CASCADE in docstrings.
4. Tags mapping: need single canonical normalizer (strip->lstrip(#)->lower->drop-empty->dedupe). Today: editor (no lower), save_prompt (lower), save_tag (none). Proposed: Tag.normalize_name + Prompt tags __post_init__, repository reuses it.
5. Numeric/bool coercion: three copies of _safe_float/_safe_int (exporter, backup). bool(x) mishandles "false". Proposed: single coercers on dataclass (_coerce_temperature/_coerce_use_count/_coerce_bool) + repo/exporter delegate.
6. VariableSpec sync: add Prompt.variable_specs() mirroring PromptTemplate.variable_specs() (both extract_variables(content+"\\n"+system)), document that variable_form/template_manager/main_window must call these (or extract_variables) never reimplement. Note main_window omits system today (divergence for callers, not models).
7. Round-trip loss table: JSON (lossless for prompts/folders/tags/templates; revisions excluded by design), CSV (currently lossy: drops folder_id/template_id/use_count - propose ADD columns backward-compatibly), Markdown (lossy by design: drops id/folder_id/template_id/use_count/is_favorite; tags unquoted - document, no reimport).

## 4. Pre-recorded implementation plan (smallest explicit change)

1. core/models.py: helpers (_ensure_id, _ensure_timestamp, _coerce_*, _normalize_*) + __post_init__ on all 6 dataclasses (coerce, never crash on None/malformed; only strip/normalize, raise only where engine requires it - default coerce-not-raise to keep Folder()/Tag() defaults working) + per-field contracts + Prompt.variable_specs().
2. storage/repository.py: orphan nullification for folder_id/template_id/parent_id before write (explicit, never crash).
3. storage/backup.py: dict.get(id) fallback (never KeyError), rely on model coercion.
4. core/exporter.py: extend CSV with folder_id,template_id,use_count (reader handles old headers), document Markdown as lossy.
5. Tests: new tests/test_models.py covering id/timestamp coercion, orphan normalization, temperature/use_count/favorite bounds, tags normalization, VariableSpec sync; keep tests/test_repository.py green.

> End of PRE-RECORD. Implementation follows; Record section appended after code+tests pass.

---

## 5. RECORD (implementation + why)

Date: 2026-09-09. Baseline full suite: 107 passed (was 90 before: +17 new model tests).

### Changed: prompt_manager/core/models.py (hardened, smallest explicit delta)
- Added module contract docstring + helpers: _ensure_ts (ISO-8601 normalize: datetime/int/SQLite-space/Z-suffix/empty->now), normalize_tag_name (canonical strip/lstrip(#)/lower), _HEX_RE/_FALSE_STRINGS.
- VariableSpec.__post_init__: name stripped; default None->""; is_multiline explicit string handling (avoids bool("false")==True); options stripped/filtered/deduped, None->[], str->single. Why: engine is validation owner for names, but model must never store None/untrimmed that breaks hydrate/has_options.
- Folder.__post_init__: blank id regenerated; name None->"" stripped; parent_id ""->None; icon blank->"folder"; sort_order int(float) fallback 0; created_at normalized. Why: PK violations + "" timestamps + malformed ints from JSON no longer persist. Note: no updated_at on Folder (documented asymmetry).
- Tag.__post_init__ + Tag.normalize_name: id ensured; name canonicalized; color #RRGGBB-validated (lowercased) else #3b82f6. Why: single canonicalizer fixes editor(no-lower)/save_prompt(lower)/save_tag(none) divergence; Prompt.tags uses it.
- PromptRevision.__post_init__: id ensured; prompt_id stripped; revision_number int floored >=1; text None->""; created_at normalized. Why: direct construction no longer violates NOT NULL/FK assumptions; repository still owns MAX+1.
- PromptTemplate.__post_init__: id ensured; name stripped (repo still owns non-empty+unique ValueError); description/content/system None->""; category strip.lower blank->"general" (mirrors repo); timestamps normalized. variable_specs() doc clarified as canonical derivation.
- Prompt.__post_init__ + Prompt.variable_specs(): id ensured; title blank->"Untitled Prompt"; folder_id/template_id ""->None; text None->""; target_model blank->"General"; temperature coerced+clamped 0.0-2.0 fallback 0.7 (NaN/inf/bool-safe); is_favorite explicit string handling; use_count int floored 0; tags canonicalized; timestamps normalized. Added variable_specs() mirroring Template (content+system via extract_variables). Why: every focus area (id stability, ISO-8601 ownership, orphans, names-vs-ids, bounds/coercion, VariableSpec sync) now explicit on the dataclass.

### Changed: prompt_manager/storage/repository.py (orphans explicit, never crash)
- save_prompt: nullifies missing folder_id/template_id via _exists checks before write (matches ON DELETE SET NULL delete semantics); docstring documents orphan policy + names<->ids mapping.
- save_folder: nullifies missing/self parent_id (self-parent treated as root); docstring added.
- Helpers: _exists/_nullify_missing_folder/_nullify_missing_template/_nullify_missing_parent. Why: SQLite FK IntegrityError on orphan insert previously crashed; now handled explicitly. Parent CASCADE (children deleted with parent) vs prompt SET NULL both documented in model docstrings.

### Changed: prompt_manager/storage/backup.py (no silent loss / no KeyError)
- import_library_from_json: f/tmpl/p id via .get(id) or None (model mints UUID, never KeyError); folder name .get default; docstring documents fallbacks + orphan nullification + revisions excluded. Why: legacy/corrupt JSON (missing ids, bad numerics) previously KeyError/crashed or stored "".

### Changed: prompt_manager/core/exporter.py (round-trip lossless where promised)
- to_csv_string: added folder_id,template_id,use_count columns; from_csv_string reads them when present, defaults when absent (backward compatible with legacy headers); docstrings document loss table. to_markdown_frontmatter docstring marks LOSSY (drops id/folder/template/use/favorite, no reimport). Why: CSV previously silently dropped folder/template/use_count (imports landed in Root with 0 uses); Markdown loss now documented not reimportable.
- _safe_float/_safe_int kept for backup/CSV call sites (model coercers are canonical for construction; helpers remain for pre-model parsing). No behavior change.

### Tests: tests/test_models.py (new, 17 tests) + existing suites
- TestModelCoercion (9): blank-id regen, timestamp ISO-8601, temperature bounds/coercion incl NaN, use_count floor, is_favorite string trap, tag canonicalization+color, folder/template/revision coercion, VariableSpec coercion, Prompt vs Template variable_specs() == extract_variables(combined) sync.
- TestRepositoryInvariants (8): orphan folder/template nullified+readable, orphan/self parent nullified, folder delete SET NULL, tags names sorted, temperature clamped on persist, CSV round-trip preserves folder/template/use_count, legacy CSV parses, JSON round-trip preserves folder/temperature.
- Full suite: 107 passed (tests/test_repository.py included and green). Covers REQUIREMENTS: every field documented (module+class docstrings), no silent loss on JSON/CSV round-trip (Markdown documented lossy), orphans explicit never-crash, tests/test_models.py (+ repository coverage).

### Remaining known limits (documented, not silently fixed)
- Tag.save_tag UPSERTs by id not name: duplicate name+different id still raises DB UNIQUE (surfaced, not swallowed); canonicalization reduces but cannot eliminate hand-built collisions.
- Prompt duplicate action drops template_id/is_favorite/use_count by design (new id); documented in pre-record, unchanged.
- save_prompt UPDATE preserves stored use_count (in-memory use_count edits ignored except via increment_use_count); toggle_favorite/increment_use_count bypass model + dont touch updated_at (documented as not content edits).
- Markdown tags use ", " join vs CSV ";" join: tags containing separators remain ambiguous (documented lossy).
- No UNIQUE(prompt_id, revision_number): concurrent MAX+1 could race (documented).
