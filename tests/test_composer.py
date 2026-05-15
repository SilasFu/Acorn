from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from acorn.composer import (
    CompositionError,
    compose_and_generate,
    merge_templates,
    resolve_chain,
)
from acorn.models import Template


def test_resolve_chain_single():
    t1 = Template(name="base", provides=["react"], files=["file1.txt"])
    with patch("acorn.composer.load_templates", return_value=[t1]):
        result = resolve_chain(["base"])
    assert len(result) == 1
    assert result[0].name == "base"


def test_resolve_chain_with_deps():
    t1 = Template(name="base", provides=["react"])
    t2 = Template(name="ext", requires=["react"], files=["file2.txt"])
    with patch("acorn.composer.load_templates", return_value=[t1, t2]):
        result = resolve_chain(["ext"])
    assert len(result) == 2
    assert result[0].name == "base"
    assert result[1].name == "ext"


def test_resolve_chain_circular():
    t1 = Template(name="a", provides=["x"], requires=["y"])
    t2 = Template(name="b", provides=["y"], requires=["x"])
    with patch("acorn.composer.load_templates", return_value=[t1, t2]):
        with pytest.raises(CompositionError, match="Circular"):
            resolve_chain(["a"])


def test_resolve_chain_not_found():
    with patch("acorn.composer.load_templates", return_value=[]):
        with pytest.raises(CompositionError, match="not found"):
            resolve_chain(["nonexistent"])


def test_merge_templates_empty():
    with pytest.raises(CompositionError):
        merge_templates([])


def test_merge_templates_single():
    t = Template(name="base", files=["a.txt"], variables=[])
    merged = merge_templates([t])
    assert merged.files == ["a.txt"]
    assert merged.name == "base"


def test_merge_templates_multiple():
    t1 = Template(name="base", files=["a.txt"], provides=["react"])
    t2 = Template(name="extra", files=["b.txt"], requires=["react"])
    merged = merge_templates([t1, t2])
    assert "a.txt" in merged.files
    assert "b.txt" in merged.files
    assert "react" in merged.provides
    assert "react" not in merged.requires  # resolved


def test_merge_templates_variable_conflict():
    from acorn.models import TemplateVariable
    t1 = Template(name="a", variables=[TemplateVariable(name="port", default="3000")])
    t2 = Template(name="b", variables=[TemplateVariable(name="port", default="8080")])
    merged = merge_templates([t1, t2])
    assert merged.variables[0].default == "3000"


def test_compose_and_generate(tmp_path: Path):
    t1 = Template(
        name="base", path=tmp_path, project_type="node",
        files=["Dockerfile"], provides=["node-runtime"],
    )
    t2 = Template(
        name="extra", files=[".env.example"], requires=["node-runtime"],
    )
    (tmp_path / "Dockerfile").write_text("FROM node")
    (tmp_path / ".env.example").write_text("PORT=3000")
    from acorn.models import GenerationOptions
    options = GenerationOptions(force=True)

    with patch("acorn.composer.load_templates", return_value=[t1, t2]):
        result = compose_and_generate(["base", "extra"], tmp_path, options)
    assert len(result) >= 2


def test_compose_and_generate_single(tmp_path: Path):
    t1 = Template(
        name="base", path=tmp_path, project_type="node",
        files=["Dockerfile"],
    )
    (tmp_path / "Dockerfile").write_text("FROM node")
    from acorn.models import GenerationOptions
    options = GenerationOptions(force=True)

    with patch("acorn.composer.load_templates", return_value=[t1]):
        result = compose_and_generate(["base"], tmp_path, options)
    assert len(result) >= 1
