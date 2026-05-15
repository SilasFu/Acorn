from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from shutil import copytree, ignore_patterns

from acorn import __version__
from acorn.analyzer import AnalyzeOptions
from acorn.analyzer import analyze as ai_analyze
from acorn.check_update import check_pypi_version
from acorn.composer import compose_and_generate
from acorn.config import (
    TEMPLATES_DIR,
    ensure_dirs,
    export_config,
    find_template_by_project_type,
    import_config,
    init_project_config,
    load_config,
    load_project_config,
    load_templates,
    remove_from_manifest,
)
from acorn.detector import detect_mixed_project, detect_project_type
from acorn.i18n import cmd_text, detect_language, set_language
from acorn.i18n import error as i18n_error
from acorn.i18n import prompt as i18n_prompt
from acorn.i18n import text as i18n_text
from acorn.log import debug as log_debug
from acorn.log import error as log_error
from acorn.log import info as log_info
from acorn.log import set_level as log_set_level
from acorn.log import warning as log_warning
from acorn.marketplace import install_from_github, search_all, search_github
from acorn.models import GenerationOptions, ProjectType
from acorn.security import format_findings, scan_template
from acorn.telemetry import is_enabled as telemetry_is_enabled
from acorn.telemetry import set_enabled as telemetry_set_enabled
from acorn.template_engine import (
    DOCKER_FILES,
    auto_generate,
    generate_from_template,
    list_templates,
    save_as_template_from_project,
)
from acorn.wizard import cmd_wizard

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_NO_MATCH = 2


def _suggest_help() -> str:
    return color(" (use --help for usage)", "dim")


def color(text: str, code: str) -> str:
    colors = {
        "green": "\033[32m",
        "yellow": "\033[33m",
        "red": "\033[31m",
        "blue": "\033[34m",
        "cyan": "\033[36m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
    }
    c = colors.get(code, "")
    reset = colors["reset"]
    return f"{c}{text}{reset}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="acorn",
        description="智能项目初始化工具 — 自动检测项目类型、匹配模板、生成配置",
        epilog=(
            "Examples:\n"
            "  acorn                      自动检测并生成配置\n"
            "  acorn --template node-api  指定模板生成\n"
            "  acorn --list              列出可用模板\n"
            "  acorn --search fastapi    搜索社区模板\n"
            "  acorn --install user/repo 安装 GitHub 模板\n"
            "  acorn --lang zh           中文模式\n"
            "  acorn --verbose           详细输出\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"acorn {__version__}")

    g_main = parser.add_argument_group("core options")
    g_main.add_argument("--wizard", action="store_true", help="启动交互式向导")
    g_main.add_argument("--template", "-t", metavar="NAME", help="指定模板名称")
    g_main.add_argument("--list", "-l", action="store_true", help="列出可用模板")
    g_main.add_argument("--add", metavar="PATH", help="添加自定义模板目录到全局模板库")
    g_main.add_argument("--remove", metavar="NAME", help="删除已安装的模板")
    g_main.add_argument("--init", action="store_true", help="在当前项目创建 .acorn/config.yaml")
    g_main.add_argument("--dir", "-d", default=".", metavar="DIR", help="目标项目目录（默认当前目录）")

    g_gen = parser.add_argument_group("generation options")
    g_gen.add_argument("--with", dest="with_templates", metavar="TEMPLATES", help="组合多个模板（逗号分隔）")
    g_gen.add_argument("--dockerize", action="store_true", help="仅生成 Docker 配置文件")
    g_gen.add_argument("--add-ci", action="store_true", help="生成 GitHub Actions CI 配置")
    g_gen.add_argument("--analyze", action="store_true", help="分析项目结构和技术栈")
    g_gen.add_argument("--allow-ai", action="store_true", help="允许 AI 辅助分析（需 API key）")
    g_gen.add_argument("--clean", action="store_true", help="清理已生成的文件")
    g_gen.add_argument("--all", action="store_true", help="配合 --clean 使用: 清理全部（含模板和配置）")
    g_gen.add_argument("--keep-templates", action="store_true", help="配合 --clean 使用: 保留模板，只删生成的文件")
    g_gen.add_argument("--force", "-f", action="store_true", help="强制覆盖已有配置")
    g_gen.add_argument("--regenerate", "-r", action="store_true", help="重新生成（自动备份原文件）")
    g_gen.add_argument("--dry-run", "-n", action="store_true", help="预览不执行")
    g_gen.add_argument("--interactive", "-i", action="store_true", help="交互式配置")
    g_gen.add_argument("--var", "-v", action="append", metavar="KEY=VALUE", help="自定义模板变量，可多次使用")
    g_gen.add_argument("--save", action="store_true", help="生成后保存为一个新模板")
    g_gen.add_argument("--save-as", metavar="NAME", help="生成后保存为新模板（指定名称）")

    g_market = parser.add_argument_group("marketplace")
    g_market.add_argument("--search", metavar="QUERY", help="搜索社区模板")
    g_market.add_argument("--install", metavar="REPO", help="从 GitHub 安装模板 (user/repo)")

    g_admin = parser.add_argument_group("administration")
    g_admin.add_argument("--completion", metavar="SHELL", help="生成 shell 自动补全脚本 (bash/zsh/fish)")
    g_admin.add_argument("--telemetry-enable", action="store_true", help="开启匿名遥测")
    g_admin.add_argument("--telemetry-disable", action="store_true", help="关闭匿名遥测")
    g_admin.add_argument("--telemetry-status", action="store_true", help="查看遥测状态")
    g_admin.add_argument("--reset", action="store_true", help="重置向导状态")
    g_admin.add_argument("--check-update", action="store_true", help="检查 PyPI 版本更新")
    g_admin.add_argument("--export", metavar="FILE", nargs="?", const="default", help="导出项目配置到文件")
    g_admin.add_argument("--import", dest="import_file", metavar="FILE", help="从文件导入项目配置")
    g_admin.add_argument("--validate", metavar="PATH", help="验证模板配置")
    g_admin.add_argument("--validate-ai-context", action="store_true", help="检查所有模板的 AI 上下文规则完整性")
    g_admin.add_argument("--scan", metavar="PATH", help="扫描模板或项目的安全问题")
    g_admin.add_argument("--config", metavar="FILE", help="指定全局配置文件路径")

    g_global = parser.add_argument_group("global options")
    g_global.add_argument("--lang", metavar="LANG", help="语言 (en/zh)")
    g_global.add_argument("--verbose", action="store_true", help="详细输出")
    g_global.add_argument("--debug", action="store_true", help="调试模式")
    g_global.add_argument("--quiet", action="store_true", help="静默模式")
    g_global.add_argument("--json", action="store_true", help="JSON 格式输出（用于脚本）")
    g_global.add_argument("--offline", action="store_true", help="离线模式（跳过网络请求）")

    return parser


def _i18n_init(args: argparse.Namespace) -> str:
    config = load_config()
    lang = args.lang or config.get("default_lang", "en")
    lang = detect_language(lang)
    set_language(lang)
    return lang


def _setup_logging(args: argparse.Namespace) -> None:
    if args.debug:
        log_set_level("DEBUG")
    elif args.quiet:
        log_set_level("ERROR")
    elif args.verbose:
        log_set_level("DEBUG")
    else:
        config = load_config()
        log_set_level(config.get("log_level", "INFO"))


def cmd_list(json_mode: bool = False) -> int:
    templates = list_templates()
    if not templates:
        log_info("No templates found.")
        return EXIT_SUCCESS

    if json_mode:
        from acorn.json_output import print_json
        print_json({"templates": templates, "count": len(templates)})
        return EXIT_SUCCESS

    title = cmd_text("list_title", count=str(len(templates)))
    print(f"\n{color(title, 'bold')}")
    print("-" * 60)
    for t in templates:
        name = color(t["name"], "cyan")
        print(f"  {name:<20} {t['description']:<30} v{t['version']}")
        if t["files"]:
            print(f"  {'':>20} files: {', '.join(t['files'])}")
        print()
    return EXIT_SUCCESS


def cmd_add(path: str) -> int:
    src = Path(path).resolve()
    if not src.is_dir():
        log_error(f"'{path}' is not a valid directory")
        return EXIT_ERROR

    template_yaml = src / "template.yaml"
    if not template_yaml.exists():
        log_error(f"No template.yaml found at {path}")
        return EXIT_ERROR

    dest = TEMPLATES_DIR / src.name
    if dest.exists():
        log_error(f"Template '{src.name}' already exists")
        return EXIT_ERROR

    ensure_dirs()
    copytree(src, dest, ignore=ignore_patterns("__pycache__", ".git"))
    log_info(f"Template '{src.name}' added to {dest}")
    print(f"{color('✓', 'green')} Template '{src.name}' added")
    return EXIT_SUCCESS


def cmd_remove(name: str) -> int:
    dest = TEMPLATES_DIR / name
    if not dest.exists():
        log_error(f"Template '{name}' not found")
        return EXIT_ERROR

    shutil.rmtree(dest)
    log_info(f"Template '{name}' removed")
    print(f"{color('✓', 'green')} Template '{name}' removed")
    return EXIT_SUCCESS


def cmd_init(args: argparse.Namespace) -> int:
    target_dir = Path(args.dir).resolve()
    if not target_dir.is_dir():
        log_error(f"Directory '{args.dir}' does not exist")
        return EXIT_ERROR

    config = init_project_config(target_dir, template_name=args.template, dry_run=args.dry_run)
    return EXIT_SUCCESS if config else EXIT_ERROR


def cmd_search(query: str, offline: bool = False) -> int:
    if offline:
        log_warning("Offline mode - skipping search")
        return EXIT_ERROR

    print(f"{color('Searching for:', 'bold')} {query}")
    results = search_all(query)
    if not results:
        results = search_github(query)

    if not results:
        log_info(f"No results found for '{query}'")
        return EXIT_NO_MATCH

    print(f"\n{color(cmd_text('search_results', query=query), 'bold')}")
    print("-" * 60)
    for r in results:
        stars = color(f"★{r['stars']}", "yellow") if r["stars"] > 0 else ""
        print(f"  {color(r['full_name'], 'cyan')} {stars}")
        if r["description"]:
            print(f"  {r['description'][:70]}")
        print()
    return EXIT_SUCCESS


def cmd_install(repo: str, dry_run: bool = False, offline: bool = False) -> int:
    if offline:
        log_warning("Offline mode - skipping install")
        return EXIT_ERROR

    if "/" not in repo:
        log_error(f"Invalid repo format '{repo}'. Use user/repo format.")
        return EXIT_ERROR

    log_info(f"Installing template from {repo}")
    result = install_from_github(repo, dry_run=dry_run)
    if result:
        print(f"{color('✓', 'green')} Template installed from {repo}")
        return EXIT_SUCCESS
    return EXIT_ERROR


def _confirm_or_exit(prompt_text: str, default_yes: bool = True) -> bool:
    default = "Y/n" if default_yes else "y/N"
    try:
        choice = input(f"{color('?', 'blue')} {prompt_text} [{default}]: ").strip().lower()
        if default_yes:
            return choice not in ("n", "no")
        return choice in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def _handle_mixed_project(target_dir: Path, options: GenerationOptions) -> str | None:
    matches = detect_mixed_project(target_dir)
    if len(matches) <= 1:
        return None

    print(f"\n{color('Detected multiple project types:', 'yellow')}")
    for i, (ptype, src, score) in enumerate(matches[:5], 1):
        print(f"  [{i}] {color(ptype.value, 'cyan')} ({src}, confidence: {score:.0%})")
    print("  [0] Cancel")

    if not options.interactive:
        best = matches[0]
        log_debug(f"Auto-selecting best match: {best[0].value}")
        return best[0].value

    try:
        choice = input(f"\n{color('?', 'blue')} Select (1-{min(len(matches), 5)}): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(matches):
                return matches[idx][0].value
    except (EOFError, KeyboardInterrupt):
        pass
    return None


def cmd_generate(args: argparse.Namespace) -> int:
    target_dir = Path(args.dir).resolve()
    if not target_dir.is_dir():
        log_error(i18n_error("dir_not_exist", dir=args.dir) + _suggest_help())
        return EXIT_ERROR

    options = GenerationOptions(
        force=args.force,
        dry_run=args.dry_run,
        interactive=args.interactive,
        regenerate=args.regenerate,
        template_name=args.template,
        save=args.save or bool(args.save_as),
        verbose=args.verbose,
        debug=args.debug,
        quiet=args.quiet,
        offline=args.offline,
        lang=args.lang,
    )

    if args.var:
        for v in args.var:
            if "=" in v:
                key, val = v.split("=", 1)
                options.variables[key.strip()] = val.strip()

    if args.template:
        generated = generate_from_template(args.template, target_dir, options)
        if options.save and not options.dry_run:
            save_name = args.save_as or target_dir.name
            save_as_template_from_project(target_dir, name=save_name, dry_run=args.dry_run)
        if options.dry_run:
            return EXIT_SUCCESS
        return EXIT_SUCCESS if generated else EXIT_ERROR

    project_config = load_project_config(target_dir)
    if "template" in project_config and not args.template:
        options.template_name = project_config["template"]
        log_info(f"Using project-config template: {options.template_name}")
        generated = generate_from_template(options.template_name, target_dir, options)
        if options.dry_run:
            return EXIT_SUCCESS
        return EXIT_SUCCESS if generated else EXIT_ERROR

    is_empty = len(list(target_dir.iterdir())) <= 1

    if is_empty:
        log_info(cmd_text("empty_project"))
        print(f"\n{color(cmd_text('empty_project'), 'yellow')}")
        if args.interactive:
            templates = load_templates()
            print(f"\n{color(cmd_text('list_title', count=str(len(templates))), 'bold')}")
            for i, t in enumerate(templates, 1):
                print(f"  [{i}] {t.name}: {t.description}")
            print("  [a] Auto-generate")

            try:
                choice = input(f"\n{color('?', 'blue')} Select: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "a"

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(templates):
                    generate_from_template(templates[idx].name, target_dir, options)
                    return EXIT_SUCCESS
            auto_generate("unknown", target_dir, options)
            return EXIT_SUCCESS
        else:
            log_info("Run with --interactive or --template")
            return EXIT_NO_MATCH

    log_info(i18n_text("detecting", path=str(target_dir)))
    print(f"{color(cmd_text('scanning'), 'bold')} in {target_dir}...")
    result = detect_project_type(target_dir)

    mixed_selection = _handle_mixed_project(target_dir, options)

    if result.project_type != ProjectType.UNKNOWN:
        confidence_display = f"{result.confidence:.0%}"
        detected_msg = i18n_text("detected", type=result.project_type.value, confidence=confidence_display)
        print(f"\n{color('√', 'green')} {detected_msg}")
        if result.framework:
            print(f"  {i18n_text('framework', name=result.framework)}")
        if result.matched_template:  # pragma: no branch (fallback always sets for detected types)
            print(f"  {i18n_text('template', name=result.matched_template)} #{color(result.project_type.value, 'cyan')}")
        if "detected_port" in result.details:
            port_msg = i18n_text("port", port=result.details["detected_port"])
            print(f"  {port_msg}")
        log_debug(f"Detection details: {result.details}")
    else:
        print(f"\n{color(i18n_text('not_detected'), 'yellow')}")

    if result.matched_template:
        if args.interactive:
            confirm_prompt = i18n_prompt("confirm_template", name=result.matched_template)
            if not _confirm_or_exit(confirm_prompt):
                templates = load_templates()
                print(f"\n{color(i18n_prompt('select_template'), 'bold')}")
                for i, t in enumerate(templates, 1):
                    print(f"  [{i}] {t.name}: {t.description}")
                try:
                    choice = input(f"\n{color('?', 'blue')} Select: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    choice = ""
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(templates):
                        generate_from_template(templates[idx].name, target_dir, options)
                        return EXIT_SUCCESS

        print()
        generated = generate_from_template(result.matched_template, target_dir, options)
        if options.save and not options.dry_run:
            save_name = args.save_as or target_dir.name
            save_as_template_from_project(target_dir, name=save_name, dry_run=args.dry_run)
        if options.dry_run:
            return EXIT_SUCCESS
        return EXIT_SUCCESS if generated else EXIT_NO_MATCH
    else:
        project_type_str = mixed_selection or (
            result.project_type.value if result.project_type != ProjectType.UNKNOWN else "unknown"
        )

        if args.interactive:
            templates = load_templates()
            title = i18n_prompt("select_template")
            print(f"\n{color(title, 'bold')}")
            for i, t in enumerate(templates, 1):
                print(f"  [{i}] {t.name}: {t.description}")
            print(f"  [a] Auto-generate for {project_type_str}")
            print("  [s] Skip")

            try:
                choice = input(f"\n{color('?', 'blue')} {i18n_prompt('select_option')}: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "s"

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(templates):
                    generate_from_template(templates[idx].name, target_dir, options)
                    return EXIT_SUCCESS
                log_info("Skipped.")
                return EXIT_NO_MATCH
            elif choice == "a":
                auto_generate(project_type_str, target_dir, options)
                return EXIT_SUCCESS
            else:
                log_info("Skipped.")
                return EXIT_NO_MATCH
        else:
            log_info(i18n_text("no_match"))
            return EXIT_NO_MATCH


def cmd_dockerize(args: argparse.Namespace) -> int:
    target_dir = Path(args.dir).resolve()
    if not target_dir.is_dir():
        log_error(f"Directory '{args.dir}' does not exist{_suggest_help()}")
        return EXIT_ERROR

    result = detect_project_type(target_dir)
    if result.project_type == ProjectType.UNKNOWN:
        log_error("Cannot detect project type in target directory")
        return EXIT_ERROR

    template_name = result.matched_template
    if not template_name:
        tpl = find_template_by_project_type(result.project_type)
        if tpl:
            template_name = tpl.name

    if not template_name:
        log_error(f"No template found for project type '{result.project_type.value}'")
        return EXIT_ERROR

    options = GenerationOptions(
        force=args.force,
        dry_run=args.dry_run,
        regenerate=args.regenerate,
        verbose=args.verbose,
        debug=args.debug,
        quiet=args.quiet,
        offline=args.offline,
        lang=args.lang,
    )

    log_info(f"Generating Docker configuration for {result.project_type.value} project...")
    generated = generate_from_template(template_name, target_dir, options, only=DOCKER_FILES)
    if not generated:
        log_info("No Docker files generated (they may already exist)")
        return EXIT_ERROR
    return EXIT_SUCCESS


CI_WORKFLOWS_DIR = ".github/workflows"
CI_FILES = {"ci.yml", "deploy.yml"}


def _ci_setup_action(project_type: str) -> str:
    setups = {
        "node": "actions/setup-node@v4\n      with:\n        node-version: '20'",
        "python": "actions/setup-python@v5\n      with:\n        python-version: '3.12'",
        "go": "actions/setup-go@v5\n      with:\n        go-version: '1.22'",
        "rust": "actions/setup-rust@v1\n      with:\n        toolchain: stable",
        "java": "actions/setup-java@v4\n      with:\n        java-version: '21'\n        distribution: temurin",
        "php": "actions/setup-php@v5\n      with:\n        php-version: '8.3'",
    }
    return setups.get(project_type, "actions/setup-node@v4\n      with:\n        node-version: '20'")


def _ci_run_command(project_type: str) -> str:
    commands = {
        "node": "npm ci\n    - run: npm test",
        "python": "pip install -r requirements.txt\n    - run: pytest",
        "go": "go mod download\n    - run: go test ./...",
        "rust": "cargo build\n    - run: cargo test",
        "java": "./mvnw verify",
        "php": "composer install\n    - run: phpunit",
    }
    return commands.get(project_type, "echo 'Run tests'")


def _generate_ci_yml(project_type: str) -> str:
    setup = _ci_setup_action(project_type)
    run = _ci_run_command(project_type)
    return f"""name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Setup
      uses: {setup}
    - name: Install dependencies
      run: {run.split(chr(10))[0]}
    - name: Test
      run: {run.split(chr(10))[-1].replace('- run: ', '') if chr(10) in run else run}
"""


def _generate_deploy_yml(project_type: str) -> str:
    return f"""name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Setup
      uses: {_ci_setup_action(project_type)}
    - name: Build
      run: {"npm run build" if project_type == "node" else "echo 'Build step not configured'"}
    - name: Deploy
      run: echo "Add your deploy steps here"
"""


def cmd_add_ci(args: argparse.Namespace) -> int:
    target_dir = Path(args.dir).resolve()
    if not target_dir.is_dir():
        log_error(f"Directory '{args.dir}' does not exist")
        return EXIT_ERROR

    result = detect_project_type(target_dir)
    if result.project_type == ProjectType.UNKNOWN:
        log_error("Cannot detect project type")
        return EXIT_ERROR

    project_type = result.project_type.value
    workflows_dir = target_dir / CI_WORKFLOWS_DIR
    workflows_dir.mkdir(parents=True, exist_ok=True)

    files_to_generate = ["ci.yml"]
    generated = []

    for fname in files_to_generate:
        dest = workflows_dir / fname
        if dest.exists() and not args.force:
            log_info(f"Skipping {CI_WORKFLOWS_DIR}/{fname} (already exists)")
            continue

        content = _generate_ci_yml(project_type) if fname == "ci.yml" else _generate_deploy_yml(project_type)

        if args.dry_run:
            print(f"  🔍 Would generate: {CI_WORKFLOWS_DIR}/{fname}")
            continue

        dest.write_text(content)
        print(f"  ✓ Generated: {CI_WORKFLOWS_DIR}/{fname}")
        generated.append(dest)

    if not generated:
        log_info("No CI files generated")
        return EXIT_ERROR
    log_info(f"Generated {len(generated)} CI workflow file(s)")
    return EXIT_SUCCESS


def cmd_analyze(args: argparse.Namespace) -> int:
    target_dir = Path(args.dir).resolve()
    if not target_dir.is_dir():
        log_error(f"Directory '{args.dir}' does not exist")
        return EXIT_ERROR

    options = AnalyzeOptions(
        allow_ai=args.allow_ai,
        dry_run=args.dry_run,
    )
    result = ai_analyze(target_dir, options)

    if args.json:
        from acorn.json_output import print_json
        data = {
            "source": result.source,
            "project_type": result.detection.project_type.value if result.detection else None,
            "confidence": result.detection.confidence if result.detection else 0,
            "framework": result.detection.framework if result.detection and result.detection.framework else None,
            "matched_template": result.detection.matched_template if result.detection and result.detection.matched_template else None,
            "ai_suggestion": result.ai_suggestion,
        }
        print_json(data)
        return EXIT_SUCCESS

    print(f"\n{color('Analysis Report', 'bold')}")
    print("=" * 50)
    if result.detection:
        d = result.detection
        project_label = i18n_text("detected", type=d.project_type.value, confidence=f"{d.confidence:.0%}")
        print(f"  {project_label}")
        if d.framework:
            print(f"  {i18n_text('framework', name=d.framework)}")
        if d.matched_template:
            print(f"  {i18n_text('template', name=d.matched_template)}")
        if d.all_matches:
            print(f"\n  {color('All matches:', 'dim')}")
            for ptype, src, score in d.all_matches:
                print(f"    - {ptype.value} ({src}, {score:.0%})")

    print(f"\n  Source: {color(result.source, 'cyan')}")
    if result.ai_suggestion:
        print(f"\n  {color('AI Suggestion:', 'bold')}")
        print(f"  {result.ai_suggestion}")
    return EXIT_SUCCESS


def cmd_clean(args: argparse.Namespace) -> int:
    import shutil as shutil_mod

    from acorn.config import load_manifest, load_project_lock
    target_dir = Path(args.dir).resolve()
    if not target_dir.is_dir():
        log_error(f"Directory '{args.dir}' does not exist")
        return EXIT_ERROR

    clean_all = args.all
    keep_templates = args.keep_templates

    if clean_all:
        acorn_dir = target_dir / ".acorn"
        if acorn_dir.exists():
            if args.dry_run:
                print(f"  🔍 Would remove: {acorn_dir}/")
            else:
                shutil_mod.rmtree(acorn_dir)
                print(f"  ✓ Removed: {acorn_dir}/")
        if not keep_templates:
            manifest = load_manifest()
            key = str(target_dir.resolve())
            if key in manifest:
                if not args.dry_run:
                    remove_from_manifest(target_dir)
                    print("  ✓ Removed from manifest")
        log_info("Clean all complete")
        return EXIT_SUCCESS

    lock = load_project_lock(target_dir)
    if not lock or "files" not in lock:
        log_info("No lock file found — nothing to clean")
        return EXIT_ERROR

    files = lock.get("files", [])
    if not files:
        log_info("No generated files recorded in lock")
        return EXIT_ERROR

    removed = 0
    for rel_path in files:
        f = target_dir / rel_path
        if f.exists():
            if args.dry_run:
                print(f"  🔍 Would remove: {rel_path}")
            else:
                f.unlink()
                print(f"  ✓ Removed: {rel_path}")
            removed += 1

    if removed == 0 and not args.dry_run:
        log_info("No files to clean")
    else:
        log_info(f"Cleaned {removed} generated file(s)")
    return EXIT_SUCCESS


def cmd_validate_ai_context() -> int:
    templates = load_templates()
    errors = []
    for tpl in templates:
        if not tpl.ai_context:
            errors.append(f"[{tpl.name}] Missing ai_context")
            continue
        cr = tpl.ai_context.cursor_rules
        if not cr.tech_stack:
            errors.append(f"[{tpl.name}] ai_context.cursor_rules.tech_stack is empty")
        if not cr.conventions:
            errors.append(f"[{tpl.name}] ai_context.cursor_rules.conventions is empty")
    if not errors:
        print(f"All {len(templates)} templates have valid AI context")
        return EXIT_SUCCESS
    for e in errors:
        print(f"  ! {e}")
    return EXIT_ERROR


def cmd_validate(path: str) -> int:
    tpl_path = Path(path).resolve()
    if not tpl_path.exists():
        log_error(f"Path not found: {path}")
        return EXIT_ERROR

    errors = []

    if tpl_path.is_dir():
        tpl_file = tpl_path / "template.yaml"
        if not tpl_file.exists():
            log_error(f"No template.yaml found in {path}")
            return EXIT_ERROR
    elif tpl_path.suffix in (".yaml", ".yml"):
        tpl_file = tpl_path
    else:
        log_error(f"Invalid template path: {path}")
        return EXIT_ERROR

    import yaml
    try:
        data = yaml.safe_load(tpl_file.read_text())
    except yaml.YAMLError as e:
        log_error(f"Invalid YAML: {e}")
        return EXIT_ERROR

    if not isinstance(data, dict):
        log_error("Template must be a YAML mapping")
        return EXIT_ERROR

    if "name" not in data:
        errors.append("Missing required field: 'name'")

    ttype = data.get("type", "unknown")
    from acorn.models import ProjectType
    try:
        ProjectType(ttype)
    except ValueError:
        errors.append(f"Invalid project type: '{ttype}'")

    ai_ctx = data.get("ai_context", {})
    if ai_ctx:
        cursor = ai_ctx.get("cursor_rules", {})
        if not cursor.get("tech_stack"):
            errors.append("ai_context.cursor_rules.tech_stack is recommended")
        if not cursor.get("conventions"):
            errors.append("ai_context.cursor_rules.conventions is recommended")

    provides = data.get("provides", [])
    requires = data.get("requires", [])
    overlap = set(provides) & set(requires)
    if overlap:
        errors.append(f"Capabilities in both provides and requires: {overlap}")

    if errors:
        for e in errors:
            print(f"  ⚠ {e}")
        return EXIT_ERROR

    print(f"  ✓ Template '{data.get('name', '?')}' is valid")
    return EXIT_SUCCESS


def cmd_completion(shell: str) -> int:
    if shell == "bash":
        print("""_acorn_completions() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    opts="--version --wizard --template --list --add --remove --init --dir --with --dockerize --add-ci --analyze --allow-ai --clean --all --keep-templates --force --regenerate --dry-run --interactive --var --save --save-as --search --install --check-update --export --import --scan --validate --validate-ai-context --config --completion --telemetry-enable --telemetry-disable --telemetry-status --reset --lang --verbose --debug --quiet --json --offline --help"
    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
}
complete -F _acorn_completions acorn""")
    elif shell == "zsh":
        print("""#compdef acorn
_acorn() {
    local -a opts
    opts=(
        '--version[show version]'
        '--wizard[interactive wizard]'
        '--template[specify template]:template:->templates'
        '--list[list templates]'
        '--add[add template]:directory:_files -/'
        '--remove[remove template]'
        '--init[init project config]'
        '--dir[target directory]:directory:_files -/'
        '--with[compose templates]'
        '--dockerize[generate Docker config]'
        '--add-ci[generate CI config]'
        '--analyze[analyze project]'
        '--allow-ai[allow AI analysis]'
        '--clean[clean generated files]'
        '--all[clean all]'
        '--keep-templates[keep templates]'
        '--force[force overwrite]'
        '--regenerate[regenerate with backup]'
        '--dry-run[preview only]'
        '--interactive[interactive mode]'
        '--var[custom variable]:variable:'
        '--save[save as template]'
        '--save-as[save template as]:name:'
        '--search[search templates]:query:'
        '--install[install template]:repo:'
        '--check-update[check for update]'
        '--export[export config]:file:_files'
        '--import[import config]:file:_files'
        '--scan[scan for security]:path:_files -/'
        '--validate[validate template]:path:_files -/'
        '--validate-ai-context[validate AI context across all templates]'
        '--config[config file]:file:_files'
        '--completion[generate completion]:shell:(bash zsh fish)'
        '--telemetry-enable[enable telemetry]'
        '--telemetry-disable[disable telemetry]'
        '--telemetry-status[telemetry status]'
        '--reset[reset wizard]'
        '--lang[language]:lang:(en zh)'
        '--verbose[verbose output]'
        '--debug[debug mode]'
        '--quiet[quiet mode]'
        '--json[JSON output]'
        '--offline[offline mode]'
        '--help[show help]'
    )
    _describe 'acorn' opts
}
compdef _acorn acorn""")
    elif shell == "fish":
        print("""complete -c acorn -l version -d 'show version'
complete -c acorn -l wizard -d 'interactive wizard'
complete -c acorn -l template -d 'specify template'
complete -c acorn -l list -d 'list templates'
complete -c acorn -l add -d 'add template directory' -r
complete -c acorn -l remove -d 'remove template' -r
complete -c acorn -l init -d 'init project config'
complete -c acorn -l dir -d 'target directory' -r
complete -c acorn -l with -d 'compose templates' -r
complete -c acorn -l dockerize -d 'generate Docker config'
complete -c acorn -l add-ci -d 'generate CI config'
complete -c acorn -l analyze -d 'analyze project'
complete -c acorn -l allow-ai -d 'allow AI analysis'
complete -c acorn -l clean -d 'clean generated files'
complete -c acorn -l all -d 'clean all'
complete -c acorn -l keep-templates -d 'keep templates'
complete -c acorn -l force -d 'force overwrite'
complete -c acorn -l regenerate -d 'regenerate with backup'
complete -c acorn -l dry-run -d 'preview only'
complete -c acorn -l interactive -d 'interactive mode'
complete -c acorn -l var -d 'custom variable' -r
complete -c acorn -l save -d 'save as template'
complete -c acorn -l save-as -d 'save template as' -r
complete -c acorn -l search -d 'search templates' -r
complete -c acorn -l install -d 'install template' -r
complete -c acorn -l check-update -d 'check for update'
complete -c acorn -l export -d 'export config' -r
complete -c acorn -l import -d 'import config' -r
complete -c acorn -l scan -d 'scan for security issues' -r
complete -c acorn -l validate -d 'validate template' -r
complete -c acorn -l validate-ai-context -d 'validate AI context'
complete -c acorn -l config -d 'config file' -r
complete -c acorn -l completion -d 'generate completion script' -r
complete -c acorn -l telemetry-enable -d 'enable telemetry'
complete -c acorn -l telemetry-disable -d 'disable telemetry'
complete -c acorn -l telemetry-status -d 'telemetry status'
complete -c acorn -l reset -d 'reset wizard state'
complete -c acorn -l lang -d 'language' -x -a 'en zh'
complete -c acorn -l verbose -d 'verbose output'
complete -c acorn -l debug -d 'debug mode'
complete -c acorn -l quiet -d 'quiet mode'
complete -c acorn -l json -d 'JSON output'
complete -c acorn -l offline -d 'offline mode'
complete -c acorn -l help -d 'show help'""")
    else:
        print(f"Unsupported shell: {shell}. Supported: bash, zsh, fish")
        return EXIT_ERROR
    return EXIT_SUCCESS


def main() -> int:
    if len(sys.argv) <= 1:
        return cmd_wizard()

    if len(sys.argv) >= 2 and sys.argv[1] == "wizard":
        sys.argv = [sys.argv[0], "--wizard"] + sys.argv[2:]

    parser = build_parser()
    args = parser.parse_args()

    if args.telemetry_enable:
        telemetry_set_enabled(True)
        return EXIT_SUCCESS
    if args.telemetry_disable:
        telemetry_set_enabled(False)
        return EXIT_SUCCESS
    if args.telemetry_status:
        status = "enabled" if telemetry_is_enabled() else "disabled"
        print(f"Telemetry: {status}")
        return EXIT_SUCCESS

    from acorn.telemetry import maybe_prompt
    maybe_prompt()

    if args.completion:
        return cmd_completion(args.completion)

    if args.config:
        config_path = Path(args.config).resolve()
        if not config_path.exists():
            log_error(f"Config file not found: {args.config}")
            return EXIT_ERROR
        CONFIG_FILE = Path.home() / ".acorn" / "config.yaml"
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(config_path), str(CONFIG_FILE))

    _i18n_init(args)
    _setup_logging(args)

    if args.debug:
        log_debug(f"acorn v{__version__}")

    if args.reset:
        return cmd_wizard(reset=True)
    if args.wizard:
        return cmd_wizard()

    if args.list:
        return cmd_list(json_mode=args.json)
    if args.add:
        return cmd_add(args.add)
    if args.remove:
        return cmd_remove(args.remove)
    if args.init:
        return cmd_init(args)
    if args.search:
        return cmd_search(args.search, offline=args.offline)
    if args.install:
        return cmd_install(args.install, dry_run=args.dry_run, offline=args.offline)
    if args.check_update:
        result = check_pypi_version(offline=args.offline)
        if result is None:
            if args.offline:
                log_warning("Offline mode — skipping update check")
            else:
                log_error("Failed to check for updates")
            return EXIT_ERROR
        print(f"Current version: {result['current']}")
        print(f"Latest version:  {result['latest']}")
        if result["upgrade_available"]:
            print(f"An upgrade is available! {result['url']}")
        else:
            print("You are up to date!")
        return EXIT_SUCCESS
    if args.validate_ai_context:
        return cmd_validate_ai_context()
    if args.validate:
        return cmd_validate(args.validate)

    if args.scan:
        scan_path_ = Path(args.scan).resolve()
        if not scan_path_.exists():
            log_error(f"Path not found: {args.scan}")
            return EXIT_ERROR
        print(f"Scanning {scan_path_}...")
        findings = scan_template(scan_path_)
        output = format_findings(findings)
        if output:
            print(output)
        else:
            print("No security issues found.")
        return EXIT_SUCCESS
    if args.export:
        target_dir = Path(args.dir).resolve()
        output_path = None
        if args.export != "default":
            output_path = Path(args.export).resolve()
        export_config(target_dir, output=output_path)
        return EXIT_SUCCESS
    if args.import_file:
        target_dir = Path(args.dir).resolve()
        source = Path(args.import_file).resolve()
        result = import_config(target_dir, source)
        return EXIT_SUCCESS if result else EXIT_ERROR

    if args.dockerize:
        return cmd_dockerize(args)
    if args.add_ci:
        return cmd_add_ci(args)
    if args.analyze:
        return cmd_analyze(args)
    if args.clean:
        return cmd_clean(args)

    if args.with_templates:
        target_dir = Path(args.dir).resolve()
        options = GenerationOptions(
            force=args.force, dry_run=args.dry_run, regenerate=args.regenerate,
            verbose=args.verbose, debug=args.debug, quiet=args.quiet, offline=args.offline, lang=args.lang,
        )
        names = [n.strip() for n in args.with_templates.split(",") if n.strip()]
        generated = compose_and_generate(names, target_dir, options)
        if args.json:
            from acorn.json_output import print_json
            print_json({"generated": [str(g) for g in generated], "count": len(generated)})
        return EXIT_SUCCESS if generated else EXIT_ERROR

    rc = cmd_generate(args)
    if args.json and rc == 0:
        from acorn.json_output import print_json
        result = detect_project_type(Path(args.dir).resolve())
        print_json({
            "status": "ok",
            "project_type": result.project_type.value,
            "matched_template": result.matched_template,
        })
    return rc


if __name__ == "__main__":
    sys.exit(main())
