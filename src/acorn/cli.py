from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from acorn import __version__
from acorn.commands.admin import cmd_check_update, cmd_completion, cmd_export, cmd_import
from acorn.commands.analyze_cmd import cmd_analyze
from acorn.commands.clean import cmd_clean
from acorn.commands.doctor import cmd_doctor
from acorn.commands.docker import cmd_add_ci, cmd_dockerize
from acorn.commands.fix import cmd_fix
from acorn.commands.generate import cmd_generate
from acorn.commands.marketplace import cmd_install, cmd_search
from acorn.commands.template_cmd import cmd_add, cmd_init, cmd_list, cmd_remove, cmd_validate, cmd_validate_ai_context
from acorn.check_update import check_pypi_version
from acorn.config import CONFIG_FILE, TEMPLATES_DIR, load_config, load_templates
from acorn.detector import detect_project_type
from acorn.format import EXIT_ERROR, EXIT_SUCCESS, color, confirm_or_exit, suggest_help
from acorn.marketplace import install_from_github, search_all, search_github
from acorn.template_engine import list_templates
from acorn.i18n import detect_language, set_language
from acorn.log import debug as log_debug, error as log_error, info as log_info, set_level as log_set_level
from acorn.log import warning as log_warning
from acorn.security import format_findings, scan_template
from acorn.telemetry import is_enabled as telemetry_is_enabled, set_enabled as telemetry_set_enabled
from acorn.wizard import cmd_wizard

_confirm_or_exit = confirm_or_exit


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

    g_fix = parser.add_argument_group("fix options")
    g_fix.add_argument("--fix", action="store_true", help="修复项目配置（子命令模式）")
    g_fix.add_argument("--fix-dockerfile", action="store_true", dest="fix_dockerfile", help="生成 Dockerfile")
    g_fix.add_argument("--fix-dockerignore", action="store_true", dest="fix_dockerignore", help="生成 .dockerignore")
    g_fix.add_argument("--fix-gitignore", action="store_true", dest="fix_gitignore", help="生成 .gitignore")
    g_fix.add_argument("--fix-cursorrules", action="store_true", dest="fix_cursorrules", help="生成 .cursorrules")
    g_fix.add_argument("--fix-claude-md", action="store_true", dest="fix_claude_md", help="生成 CLAUDE.md")
    g_fix.add_argument("--fix-copilot", action="store_true", dest="fix_copilot", help="生成 GitHub Copilot instructions")
    g_fix.add_argument("--fix-ai", action="store_true", dest="fix_ai", help="生成所有 AI 配置文件")
    g_fix.add_argument("--fix-all", action="store_true", dest="fix_all", help="修复所有可自动修复项")

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


def main() -> int:
    if len(sys.argv) <= 1:
        return cmd_doctor()

    if len(sys.argv) >= 2 and sys.argv[1] == "wizard":
        sys.argv = [sys.argv[0], "--wizard"] + sys.argv[2:]
    if len(sys.argv) >= 2 and sys.argv[1] == "fix":
        sys.argv = [sys.argv[0], "--fix"] + sys.argv[2:]

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
        return cmd_check_update(offline=args.offline)
    if args.validate_ai_context:
        return cmd_validate_ai_context()
    if args.validate:
        return cmd_validate(args.validate)

    if args.fix:
        return cmd_fix(args)

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
        return cmd_export(args)
    if args.import_file:
        return cmd_import(args)

    if args.dockerize:
        return cmd_dockerize(args)
    if args.add_ci:
        return cmd_add_ci(args)
    if args.analyze:
        return cmd_analyze(args)
    if args.clean:
        return cmd_clean(args)

    if args.with_templates:
        from acorn.composer import compose_and_generate
        from acorn.models import GenerationOptions
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
