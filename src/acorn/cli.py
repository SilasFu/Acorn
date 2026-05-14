from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from shutil import copytree, ignore_patterns

from acorn import __version__
from acorn.check_update import check_pypi_version
from acorn.config import (
    TEMPLATES_DIR,
    ensure_dirs,
    export_config,
    import_config,
    init_project_config,
    load_config,
    load_project_config,
    load_templates,
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
from acorn.template_engine import (
    auto_generate,
    generate_from_template,
    list_templates,
    save_as_template_from_project,
)

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_NO_MATCH = 2


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
    g_main.add_argument("--template", "-t", metavar="NAME", help="指定模板名称")
    g_main.add_argument("--list", "-l", action="store_true", help="列出可用模板")
    g_main.add_argument("--add", metavar="PATH", help="添加自定义模板目录到全局模板库")
    g_main.add_argument("--remove", metavar="NAME", help="删除已安装的模板")
    g_main.add_argument("--init", action="store_true", help="在当前项目创建 .acorn/config.yaml")
    g_main.add_argument("--dir", "-d", default=".", metavar="DIR", help="目标项目目录（默认当前目录）")

    g_gen = parser.add_argument_group("generation options")
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
    g_admin.add_argument("--check-update", action="store_true", help="检查 PyPI 版本更新")
    g_admin.add_argument("--export", metavar="FILE", nargs="?", const="default", help="导出项目配置到文件")
    g_admin.add_argument("--import", dest="import_file", metavar="FILE", help="从文件导入项目配置")
    g_admin.add_argument("--scan", metavar="PATH", help="扫描模板或项目的安全问题")
    g_admin.add_argument("--config", metavar="FILE", help="指定全局配置文件路径")

    g_global = parser.add_argument_group("global options")
    g_global.add_argument("--lang", metavar="LANG", help="语言 (en/zh)")
    g_global.add_argument("--verbose", action="store_true", help="详细输出")
    g_global.add_argument("--debug", action="store_true", help="调试模式")
    g_global.add_argument("--quiet", action="store_true", help="静默模式")
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


def cmd_list() -> int:
    templates = list_templates()
    if not templates:
        log_info("No templates found.")
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
        log_error(i18n_error("dir_not_exist", dir=args.dir))
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
        if result.matched_template:
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


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

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

    if args.list:
        return cmd_list()
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
    if args.scan:
        scan_path = Path(args.scan).resolve()
        if not scan_path.exists():
            log_error(f"Path not found: {args.scan}")
            return EXIT_ERROR
        print(f"Scanning {scan_path}...")
        findings = scan_template(scan_path)
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

    return cmd_generate(args)


if __name__ == "__main__":
    sys.exit(main())
