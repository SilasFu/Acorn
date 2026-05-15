from __future__ import annotations

from pathlib import Path
from typing import Any

from acorn.config import load_templates
from acorn.log import error as log_error
from acorn.log import info as log_info
from acorn.log import warning as log_warning
from acorn.models import GenerationOptions, Template, TemplateVariable


class CompositionError(Exception):
    pass


def _build_capability_map(templates: list[Template]) -> dict[str, Template]:
    cap_map: dict[str, Template] = {}
    for t in templates:
        for cap in t.provides:
            if cap in cap_map:
                log_warning(f"Capability '{cap}' provided by multiple templates: '{cap_map[cap].name}' and '{t.name}'")
            cap_map[cap] = t
    return cap_map


def resolve_chain(names: list[str]) -> list[Template]:
    all_templates = {t.name: t for t in load_templates()}
    cap_map = _build_capability_map(list(all_templates.values()))
    resolved: list[Template] = []
    seen_names: set[str] = set()
    seen_caps: set[str] = set()

    def _resolve_one(name: str, trail: set[str]) -> Template:
        if name in trail:
            raise CompositionError(f"Circular dependency: {' -> '.join(trail | {name})}")
        tpl = all_templates.get(name)
        if not tpl:
            raise CompositionError(f"Template '{name}' not found")
        trail = trail | {name}
        for cap in tpl.requires:
            if cap in seen_caps:
                continue
            provider = cap_map.get(cap)
            if provider and provider.name not in seen_names:
                _resolve_one(provider.name, trail)
            seen_caps.add(cap)
        if name not in seen_names:
            resolved.append(tpl)
            seen_names.add(name)
            seen_caps.update(tpl.provides)
        return tpl

    for n in names:
        _resolve_one(n, set())
    return resolved


def merge_templates(templates: list[Template]) -> Template:
    if not templates:
        raise CompositionError("No templates to compose")
    base = templates[0]
    all_files: list[str] = list(base.files)
    all_vars: dict[str, TemplateVariable] = {v.name: v for v in base.variables}
    all_provides: set[str] = set(base.provides)
    all_requires: set[str] = set(base.requires)
    all_ai_contexts: list[dict[str, Any]] = []
    if base.ai_context:
        all_ai_contexts.append({
            "tech_stack": base.ai_context.cursor_rules.tech_stack,
            "conventions": base.ai_context.cursor_rules.conventions,
        })

    for tpl in templates[1:]:
        for f in tpl.files:
            if f not in all_files:
                all_files.append(f)
        for v in tpl.variables:
            if v.name not in all_vars:
                all_vars[v.name] = v
            elif v.default != all_vars[v.name].default:
                log_warning(f"Variable '{v.name}' conflict: '{all_vars[v.name].default}' vs '{v.default}' — using first")
        all_provides.update(tpl.provides)
        all_requires.update(tpl.requires)
        if tpl.ai_context:
            all_ai_contexts.append({
                "tech_stack": tpl.ai_context.cursor_rules.tech_stack,
                "conventions": tpl.ai_context.cursor_rules.conventions,
            })

    from acorn.models import AIContext, CursorRules

    merged_ai = None
    if all_ai_contexts:
        merged_tech = "; ".join(c["tech_stack"] for c in all_ai_contexts if c["tech_stack"])
        merged_conv: list[str] = []
        for c in all_ai_contexts:
            merged_conv.extend(c["conventions"])
        merged_ai = AIContext(cursor_rules=CursorRules(tech_stack=merged_tech, conventions=merged_conv))

    resolved_requires = all_requires - all_provides
    if resolved_requires:
        log_warning(f"Unresolved dependencies: {', '.join(resolved_requires)}")

    return Template(
        name="+".join(t.name for t in templates),
        description="Composed: " + ", ".join(t.name for t in templates),
        path=base.path,
        project_type=base.project_type,
        files=all_files,
        variables=list(all_vars.values()),
        provides=list(all_provides),
        requires=list(resolved_requires),
        ai_context=merged_ai,
    )


def compose_and_generate(
    template_names: list[str],
    output_dir: Path,
    options: GenerationOptions,
) -> list[Path]:
    from acorn.template_engine import generate_from_template
    templates = resolve_chain(template_names)
    merged = merge_templates(templates)

    log_info(f"Composing {len(templates)} template(s): {', '.join(t.name for t in templates)}")
    log_info(f"Merged template: {merged.name}")
    log_info(f"Files: {len(merged.files)}")

    try:
        return generate_from_template(merged.name, output_dir, options, template=merged)
    except Exception:
        log_error("Failed to compose templates")
        return []
