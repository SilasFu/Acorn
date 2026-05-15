from __future__ import annotations

import json
import sys
from pathlib import Path

from acorn.analysis.health import diagnose
from acorn.analysis.health_rules import CheckCategory, CheckPriority
from acorn.analysis.insights import has_source_code
from acorn import __version__
from acorn.config import load_config
from acorn.format import color, confirm_or_exit, EXIT_SUCCESS
from acorn.i18n import detect_language, set_language, t
from acorn.log import info as log_info


def _msg(key: str, fallback: str = "") -> str:
    val = t(key)
    return val if val != key else fallback


def _display_report(report) -> None:
    name = report.project_path.name
    title = _msg("messages.doctor_title", f"Project Report — {name}")
    print(f"\n{color(title, 'bold')}")

    type_str = f"{report.project_type}"
    if report.framework:
        type_str += f" ({report.framework})"
    print(f"  {_msg('messages.project_type', 'Type')}: {type_str} ({_msg('messages.confidence', 'confidence')}: {report.confidence:.0%})")

    sections = [
        (CheckCategory.AI_READINESS, "messages.ai_readiness", "🤖"),
        (CheckCategory.DEVOPS, "messages.devops", "🐳"),
        (CheckCategory.CODE_QUALITY, "messages.code_quality", "📋"),
    ]

    for cat, key, icon in sections:
        cat_checks = [c for c in report.checks if c.category == cat]
        if not cat_checks:
            continue
        print(f"\n  {icon} {_msg(key, key)}")
        for c in cat_checks:
            mark = color("✓", "green") if c.status else color("✗", "red")
            label = f"check_{c.name}_present" if c.status else f"check_{c.name}_absent"
            msg = _msg(f"messages.{label}", "")
            print(f"    {mark} {c.name:<30} {msg}")
            if not c.status and c.fix_target and c.auto_fixable:
                print(f"      [{color('acorn fix --' + c.fix_target, 'dim')}]")

    print(f"\n  {'═' * 50}")
    s = report.summary
    print(f"  {color('✓', 'green')} {s['passed']} {_msg('messages.passed', 'passed')}  "
          f"{color('✗', 'red')} {s['failed']} {_msg('messages.failed', 'failed')}")


VERSION_CHECK_FILE = Path.home() / ".acorn" / "version-check.json"


def _check_version() -> None:
    from acorn.check_update import check_pypi_version
    VERSION_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if VERSION_CHECK_FILE.exists():
        try:
            data = json.loads(VERSION_CHECK_FILE.read_text())
            import time
            if time.time() - data.get("checked", 0) < 86400:
                return
        except (OSError, json.JSONDecodeError):
            pass
    result = check_pypi_version(offline=False)
    if result and result["upgrade_available"]:
        print(f"\n  {color('⟳', 'yellow')} {_msg('messages.update_available', 'Update available')}: "
              f"v{__version__} → {color('v' + result['latest'], 'green')}")
        print(f"    {result['url']}")
    try:
        import time
        VERSION_CHECK_FILE.write_text(json.dumps({"checked": time.time()}))
    except OSError:
        pass


def cmd_doctor() -> int:
    cwd = Path.cwd()

    if not has_source_code(cwd):
        from acorn.wizard import cmd_wizard
        return cmd_wizard()

    config = load_config()
    lang = config.get("default_lang", "en")
    lang = detect_language(lang)
    set_language(lang)

    from acorn.telemetry import maybe_prompt
    maybe_prompt()

    report = diagnose(cwd)

    if "--json" in sys.argv or "-j" in sys.argv:
        import json
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return EXIT_SUCCESS

    _display_report(report)

    _check_version()

    failed_auto = [c for c in report.checks if not c.status and c.auto_fixable]
    if failed_auto:
        prompt_text = _msg("messages.fix_prompt", "Fix all auto-fixable items?")
        if confirm_or_exit(prompt_text):
            from acorn.commands.fix import fix_all
            scope = {c.fix_target for c in failed_auto if c.fix_target}
            return fix_all(cwd, scope=scope) if scope else EXIT_SUCCESS

    return EXIT_SUCCESS
