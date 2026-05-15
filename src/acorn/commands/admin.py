from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from acorn.check_update import check_pypi_version
from acorn.config import export_config, import_config
from acorn.format import EXIT_SUCCESS, EXIT_ERROR
from acorn.log import error as log_error, warning as log_warning


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


def cmd_check_update(offline: bool = False) -> int:
    result = check_pypi_version(offline=offline)
    if result is None:
        if offline:
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


def cmd_export(args: argparse.Namespace) -> int:
    target_dir = Path(args.dir).resolve()
    output_path = None
    if args.export != "default":
        output_path = Path(args.export).resolve()
    export_config(target_dir, output=output_path)
    return EXIT_SUCCESS


def cmd_import(args: argparse.Namespace) -> int:
    target_dir = Path(args.dir).resolve()
    source = Path(args.import_file).resolve()
    result = import_config(target_dir, source)
    return EXIT_SUCCESS if result else EXIT_ERROR
