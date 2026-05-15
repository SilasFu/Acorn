from __future__ import annotations

import argparse
from pathlib import Path

from acorn.config import (
    load_project_config,
    load_templates,
)
from acorn.detector import detect_mixed_project, detect_project_type
from acorn.format import color, suggest_help, EXIT_SUCCESS, EXIT_ERROR, EXIT_NO_MATCH
from acorn.i18n import cmd_text, error as i18n_error, prompt as i18n_prompt, text as i18n_text
from acorn.log import debug as log_debug, error as log_error, info as log_info
from acorn.models import GenerationOptions, ProjectType
from acorn.template_engine import auto_generate, generate_from_template, list_templates, save_as_template_from_project


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
        log_error(i18n_error("dir_not_exist", dir=args.dir) + suggest_help())
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
            from acorn.format import confirm_or_exit
            if not confirm_or_exit(i18n_prompt("confirm_template", name=result.matched_template)):
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
