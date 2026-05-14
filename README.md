# acorn

智能项目初始化工具 — 自动检测项目类型、匹配模板、生成 Docker/devcontainer 配置。

Smart project initializer — auto-detects project types, matches templates, generates Docker/devcontainer config files.

## Installation

```bash
pip install acorn
```

For extra features:

```bash
pip install acorn[color]  # colorama support
pip install acorn[network] # marketplace & update checks
pip install acorn[advanced] # Jinja2 template engine
pip install acorn[all]   # all extras
```

## Quick Start

```bash
# Auto-detect current project and generate config
init-project

# Auto-detect a specific directory
acorn dir /path/to/project

# List available templates
acorn list

# Generate from a specific template
acorn template python-fastapi

# Generate into a specific directory
acorn template node-api --dir ./my-app
```

## Usage

### Core Options

| Flag | Description |
|------|-------------|
| `--template, -t NAME` | Specify template by name |
| `--list, -l` | List available templates |
| `--add PATH` | Add a custom template directory |
| `--remove NAME` | Remove an installed template |
| `--init` | Create `.acorn/config.yaml` in current project |
| `--dir, -d DIR` | Target project directory (default: `.`) |

### Generation Options

| Flag | Description |
|------|-------------|
| `--force, -f` | Overwrite existing files |
| `--regenerate, -r` | Regenerate (auto-backup originals) |
| `--dry-run, -n` | Preview without writing |
| `--interactive, -i` | Interactive configuration |
| `--var, -v KEY=VALUE` | Set template variables (repeatable) |
| `--save` | Save generated output as a new template |
| `--save-as NAME` | Save as new template with given name |

### Marketplace

| Flag | Description |
|------|-------------|
| `--search QUERY` | Search community templates on GitHub |
| `--install REPO` | Install template from GitHub (`user/repo`) |

### Administration

| Flag | Description |
|------|-------------|
| `--check-update` | Check for new version on PyPI |
| `--export [FILE]` | Export project config to file |
| `--import FILE` | Import project config from file |
| `--scan PATH` | Scan template/project for security issues |
| `--config FILE` | Use a custom global config file |

### Global Options

| Flag | Description |
|------|-------------|
| `--lang LANG` | Language (`en` or `zh`) |
| `--verbose` | Verbose output |
| `--debug` | Debug mode |
| `--quiet` | Silent mode (errors only) |
| `--offline` | Offline mode (skip network requests) |
| `--version` | Show version |

## Examples

```bash
# Detect project type and generate config
cd my-node-project
init-project

# Specify template with custom variables
acorn template python-fastapi --var port=8080 --var app_name=myservice

# Interactive mode with template selection
acorn interactive

# Dry run to preview changes
acorn dry-run

# Scan an existing template for security issues
acorn scan ./my-template

# Search and install community templates
acorn search fastapi
acorn install user/init-template-fastapi

# Export and import project configuration
acorn export my-config.yaml
acorn import my-config.yaml

# Use Chinese language
acorn lang zh
```

## Project Config

Create a project-level config to lock template selection:

```bash
acorn init --template python-fastapi
```

This creates `.acorn/config.yaml` in your project directory. The template will be used automatically on subsequent runs.

## Templates

Built-in templates:

| Template | Description |
|----------|-------------|
| `node-api` | Node.js Express API |
| `python-fastapi` | Python FastAPI service |
| `react-vite` | React + Vite frontend |
| `golang-gin` | Go Gin web framework |
| `java-spring` | Java Spring Boot |
| `ruby-rails` | Ruby on Rails |
| `php-laravel` | PHP Laravel |
| `deno-app` | Deno application |
| `bun-app` | Bun application |

## Template Development

Templates are defined with a `template.yaml`:

```yaml
name: my-template
description: My custom template
version: 1.0.0
type: python
files:
 - Dockerfile
 - docker-compose.yml
 - .env.example
variables:
 - name: port
  default: "8000"
  prompt: "Application port"
 - name: app_name
  default: "myapp"
detectors:
 files:
  - requirements.txt
  - pyproject.toml
 keywords:
  - fastapi
  - django
```

See [DESIGN.md](DESIGN.md) for full template specification.

## Configuration

Global config file: `~/.acorn/config.yaml`

```yaml
default_lang: en
log_level: INFO
offline: false
```

## Extending

### Plugins

Place Python plugins in `~/.config/acorn/plugins/`:

```python
def before_detect(context):
  # Modify detection context
  return context

def after_generate(context):
  # Post-generation hook
  return context
```

### Custom Commands

Place executable scripts in `~/.config/acorn/commands/` for custom CLI commands.

## License

MIT
