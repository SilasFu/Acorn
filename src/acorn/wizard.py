from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from acorn.config import load_config
from acorn.i18n import detect_language, set_language
from acorn.log import info as log_info
from acorn.models import GenerationOptions

CHECKPOINT_FILE = Path.home() / ".acorn" / "wizard-checkpoint.json"


class WizardOption:
    def __init__(self, label: str, value: Any) -> None:
        self.label = label
        self.value = value


class WizardStep:
    def __init__(
        self,
        key: str,
        prompt: str,
        prompt_zh: str | None = None,
        input_type: str = "text",
        options: list[WizardOption] | None = None,
        default: Any = None,
        validator: Callable[[str], bool] | None = None,
    ) -> None:
        self.key = key
        self.prompt = prompt
        self.prompt_zh = prompt_zh
        self.input_type = input_type
        self.options = options
        self.default = default
        self.validator = validator


def _ask(step: WizardStep, lang: str) -> Any:
    prompt = step.prompt_zh if lang == "zh" and step.prompt_zh else step.prompt
    if step.input_type == "select":
        print(f"\n{prompt}")
        for i, opt in enumerate(step.options or [], 1):
            print(f"  [{i}] {opt.label}")
        if step.default is not None:
            print(f"  [0] {step.default}")
        while True:
            try:
                raw = input(f"\n? Select [1-{len(step.options or [])}]: ").strip()
            except (EOFError, KeyboardInterrupt):
                raw = ""
            if not raw and step.default is not None:
                return step.default
            if raw.isdigit():
                idx = int(raw) - 1
                if step.options and 0 <= idx < len(step.options):
                    return step.options[idx].value
            print("Invalid selection.")
    elif step.input_type == "confirm":
        default_str = "Y/n" if step.default is True else "y/N"
        try:
            raw = input(f"\n{prompt} [{default_str}]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            raw = ""
        if not raw:
            return step.default if step.default is not None else True
        return raw in ("y", "yes")
    else:
        default_str = f" [{step.default}]" if step.default is not None else ""
        try:
            raw = input(f"\n{prompt}{default_str}: ").strip()
        except (EOFError, KeyboardInterrupt):
            raw = ""
        if not raw and step.default is not None:
            return step.default
        if step.validator and not step.validator(raw):
            print("Invalid input.")
            return _ask(step, lang)
        return raw


_STEPS: list[WizardStep] = [
    WizardStep(
        key="name",
        prompt="Project name",
        prompt_zh="项目名称",
        input_type="text",
        default="my-app",
    ),
    WizardStep(
        key="project_type",
        prompt="Project type",
        prompt_zh="项目类型",
        input_type="select",
        options=[
            WizardOption("Web API service", "api"),
            WizardOption("Frontend application", "frontend"),
            WizardOption("Backend service", "backend"),
            WizardOption("Full-stack application", "fullstack"),
            WizardOption("I don't know, you decide", "auto"),
        ],
    ),
    WizardStep(
        key="language",
        prompt="Language / runtime",
        prompt_zh="技术栈偏好",
        input_type="select",
        options=[
            WizardOption("Node.js", "node"),
            WizardOption("Python", "python"),
            WizardOption("Go", "go"),
            WizardOption("Rust", "rust"),
            WizardOption("Java", "java"),
            WizardOption("PHP", "php"),
            WizardOption("Ruby", "ruby"),
            WizardOption("Deno", "deno"),
            WizardOption("Bun", "bun"),
            WizardOption("Any / Auto-detect", "auto"),
        ],
        default="Auto-detect",
    ),
    WizardStep(
        key="docker",
        prompt="Generate Docker configuration?",
        prompt_zh="需要 Docker 配置吗？",
        input_type="confirm",
        default=True,
    ),
    WizardStep(
        key="ci",
        prompt="Generate CI/CD (GitHub Actions)?",
        prompt_zh="需要 CI/CD 配置吗？",
        input_type="confirm",
        default=True,
    ),
    WizardStep(
        key="devcontainer",
        prompt="Generate Dev Container configuration?",
        prompt_zh="需要开发容器 (Dev Container) 配置吗？",
        input_type="confirm",
        default=False,
    ),
    WizardStep(
        key="open_editor",
        prompt="Open in VS Code / Cursor after generation?",
        prompt_zh="生成后用 VS Code / Cursor 打开吗？",
        input_type="confirm",
        default=True,
    ),
]


def _map_to_options(answers: dict[str, Any], lang: str) -> GenerationOptions:

    language = answers.get("language", "auto")

    target_type = None
    if language != "auto":
        target_type = language

    name = answers.get("name", "my-app")
    target_dir = Path.cwd() / name

    options = GenerationOptions(
        force=True,
        dry_run=False,
        interactive=False,
        verbose=True,
        lang=lang,
    )
    options.variables["project_name"] = name
    return options, target_dir, target_type


def _save_checkpoint(answers: dict[str, Any], step_index: int) -> None:
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"answers": answers, "step_index": step_index}
    CHECKPOINT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _load_checkpoint() -> tuple[dict[str, Any], int] | None:
    if not CHECKPOINT_FILE.exists():
        return None
    try:
        data = json.loads(CHECKPOINT_FILE.read_text())
        return data.get("answers", {}), data.get("step_index", 0)
    except (json.JSONDecodeError, KeyError):
        return None


def _clear_checkpoint() -> None:
    CHECKPOINT_FILE.unlink(missing_ok=True)


def cmd_wizard(reset: bool = False) -> int:
    config = load_config()
    lang = config.get("default_lang", "en")
    lang = detect_language(lang)
    set_language(lang)

    title = "Welcome to Acorn! Let me help you initialize a project."
    title_zh = "欢迎使用 Acorn！我来帮你初始化项目。"
    print(f"\n{'=' * 50}")
    print(title_zh if lang == "zh" else title)
    print(f"{'=' * 50}")

    if reset:
        _clear_checkpoint()

    checkpoint = _load_checkpoint()
    answers: dict[str, Any] = checkpoint[0] if checkpoint else {}
    start_step = checkpoint[1] if checkpoint else 0

    if start_step > 0:
        log_info(f"Resuming from step {start_step + 1}...")

    for i, step in enumerate(_STEPS):
        if i < start_step:
            continue
        if step.key in answers and answers[step.key] is not None:
            continue
        answers[step.key] = _ask(step, lang)
        _save_checkpoint(answers, i + 1)

    _clear_checkpoint()

    options, target_dir, target_type = _map_to_options(answers, lang)
    target_dir.mkdir(parents=True, exist_ok=True)

    from acorn.cli import build_parser
    parser = build_parser()
    ns_args = [
        "acorn",
        "--dir", str(target_dir),
        "--force",
        "--verbose",
        "--lang", lang,
    ]
    if answers.get("docker"):
        ns_args.append("--force")
    if target_type:
        ns_args.extend(["--template", target_type])

    args = parser.parse_args(ns_args[1:])

    from acorn.commands.generate import cmd_generate
    rc = cmd_generate(args)

    if rc == 0 and answers.get("open_editor"):
        editor = _detect_editor()
        if editor:
            import subprocess
            subprocess.Popen([editor, str(target_dir)])

    return rc


def _detect_editor() -> str | None:
    import shutil
    for editor in ["cursor", "code", "vscode", "idea"]:
        if shutil.which(editor):
            return editor
    return None
