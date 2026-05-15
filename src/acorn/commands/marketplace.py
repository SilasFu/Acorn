from __future__ import annotations

from acorn.format import EXIT_ERROR, EXIT_NO_MATCH, EXIT_SUCCESS, color
from acorn.i18n import cmd_text
from acorn.log import error as log_error
from acorn.log import info as log_info
from acorn.log import warning as log_warning
from acorn.marketplace import install_from_github, search_all, search_github


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
