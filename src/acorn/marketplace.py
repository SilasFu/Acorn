from __future__ import annotations

import json
import shutil
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from acorn.config import TEMPLATES_DIR

GITHUB_API = "https://api.github.com"
TIMEOUT = 10


def _github_get(path: str) -> dict[str, Any] | list[Any] | None:
    url = f"{GITHUB_API}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "init-project"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError):
        return None


def search_github(query: str, limit: int = 10) -> list[dict[str, Any]]:
    q = f"acorn-{query}+in:name+topic:acorn"
    result = _github_get(f"/search/repositories?q={q}&per_page={limit}&sort=updated")
    if isinstance(result, dict):
        items = result.get("items", [])
        return [
            {
                "name": repo.get("name", "").replace("acorn-", ""),
                "full_name": repo.get("full_name", ""),
                "description": repo.get("description", "") or "",
                "stars": repo.get("stargazers_count", 0),
                "url": repo.get("html_url", ""),
                "updated_at": repo.get("updated_at", ""),
            }
            for repo in items
        ]
    return []


def search_all(query: str, limit: int = 10) -> list[dict[str, Any]]:
    q = f"{query}+topic:acorn"
    result = _github_get(f"/search/repositories?q={q}&per_page={limit}&sort=updated")
    if isinstance(result, dict):
        items = result.get("items", [])
        return [
            {
                "name": repo.get("name", "").replace("acorn-", ""),
                "full_name": repo.get("full_name", ""),
                "description": repo.get("description", "") or "",
                "stars": repo.get("stargazers_count", 0),
                "url": repo.get("html_url", ""),
                "updated_at": repo.get("updated_at", ""),
            }
            for repo in items
        ]
    return []


def install_from_github(repo_full_name: str, dry_run: bool = False) -> Path | None:
    archive_url = f"https://github.com/{repo_full_name}/archive/refs/heads/main.zip"

    if dry_run:
        print(f"  🔍 Would install {repo_full_name} from {archive_url}")
        return None

    tmp_dir = Path(tempfile.mkdtemp(prefix="acorn-"))
    zip_path = tmp_dir / "repo.zip"

    try:
        req = urllib.request.Request(archive_url, headers={"User-Agent": "init-project"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            zip_path.write_bytes(resp.read())
    except (urllib.error.URLError, OSError) as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"✗ Failed to download {repo_full_name}: {e}")
        return None

    import zipfile
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)
    except zipfile.BadZipFile:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"✗ Invalid archive for {repo_full_name}")
        return None

    extracted_dirs = [d for d in tmp_dir.iterdir() if d.is_dir()]
    if not extracted_dirs:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"✗ No content found in {repo_full_name}")
        return None

    repo_dir = extracted_dirs[0]
    template_yaml = repo_dir / "template.yaml"
    if not template_yaml.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"✗ No template.yaml found in {repo_full_name}")
        return None

    import yaml
    raw = template_yaml.read_text()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        data = None
    if not data or "name" not in data:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"✗ Invalid template.yaml in {repo_full_name}")
        return None

    template_name = data["name"]
    dest = TEMPLATES_DIR / template_name
    if dest.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"✗ Template '{template_name}' already exists")
        return None

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo_dir, dest, ignore=shutil.ignore_patterns("__pycache__", ".git"))
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"✓ Template '{template_name}' installed from {repo_full_name}")
    return dest
