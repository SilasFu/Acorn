from __future__ import annotations

import argparse
from pathlib import Path

from acorn.analyzer import AnalyzeOptions
from acorn.analyzer import analyze as ai_analyze
from acorn.format import EXIT_ERROR, EXIT_SUCCESS, color
from acorn.i18n import text as i18n_text
from acorn.log import error as log_error


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
