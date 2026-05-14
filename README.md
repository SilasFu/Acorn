# Acorn

智能项目初始化工具 — 自动检测项目类型、匹配模板、生成 Docker/devcontainer 配置。

Smart project initializer — auto-detects project types, matches templates, generates Docker/devcontainer config files.

---

## Installation / 安装

```bash
pip install acorn
```

可选扩展 / Optional extras:

```bash
pip install acorn[color]    # 彩色输出 / colored output
pip install acorn[network]  # 市场搜索和更新检查 / marketplace & update checks
pip install acorn[advanced] # Jinja2 模板引擎 / Jinja2 template engine
pip install acorn[all]      # 全部 / all extras
```

---

## Quick Start / 快速开始

```bash
# 自动检测当前目录并生成配置 / Auto-detect and generate
acorn

# 指定目标目录 / Specify target directory
acorn --dir /path/to/project

# 列出可用模板 / List available templates
acorn --list

# 从指定模板生成 / Generate from a template
acorn --template python-fastapi

# 交互式选择 / Interactive mode
acorn --interactive

# 中文模式 / Chinese language mode
acorn --lang zh

# 预览不执行 / Dry run (preview without writing)
acorn --dry-run
```

---

## Usage / 使用说明

### 核心选项 / Core Options

| 选项 / Flag | 说明 / Description |
|-------------|-------------------|
| `--dir, -d DIR` | 目标项目目录（默认当前目录）/ Target directory (default: `.`) |
| `--template, -t NAME` | 指定模板 / Specify template by name |
| `--list, -l` | 列出可用模板 / List available templates |
| `--add PATH` | 添加自定义模板目录 / Add custom template directory |
| `--remove NAME` | 删除已安装模板 / Remove installed template |
| `--init` | 在项目中创建 `.acorn/config.yaml` / Create project config |

### 生成选项 / Generation Options

| 选项 / Flag | 说明 / Description |
|-------------|-------------------|
| `--interactive, -i` | 交互式配置 / Interactive configuration |
| `--force, -f` | 强制覆盖已有文件 / Overwrite existing files |
| `--regenerate, -r` | 重新生成（自动备份原文件）/ Regenerate (auto-backup) |
| `--dry-run, -n` | 预览不执行 / Preview without writing |
| `--var, -v KEY=VALUE` | 自定义模板变量，可多次使用 / Set template variables (repeatable) |
| `--save` | 生成后保存为新模板 / Save output as new template |
| `--save-as NAME` | 指定名称保存为新模板 / Save as new template with name |

### 市场 / Marketplace

| 选项 / Flag | 说明 / Description |
|-------------|-------------------|
| `--search QUERY` | 搜索社区模板 / Search community templates on GitHub |
| `--install REPO` | 安装模板 (`user/repo`) / Install template from GitHub |

### 管理 / Administration

| 选项 / Flag | 说明 / Description |
|-------------|-------------------|
| `--check-update` | 检查 PyPI 版本更新 / Check for new version on PyPI |
| `--export [FILE]` | 导出项目配置 / Export project config |
| `--import FILE` | 导入项目配置 / Import project config |
| `--scan PATH` | 扫描安全问题 / Scan for security issues |
| `--config FILE` | 指定全局配置文件 / Use custom config file |

### 全局选项 / Global Options

| 选项 / Flag | 说明 / Description |
|-------------|-------------------|
| `--lang LANG` | 语言 `en` 或 `zh` / Language |
| `--verbose` | 详细输出 / Verbose output |
| `--debug` | 调试模式 / Debug mode |
| `--quiet` | 静默模式（仅错误）/ Silent (errors only) |
| `--offline` | 离线模式 / Offline mode |
| `--version` | 显示版本 / Show version |

---

## Examples / 示例

```bash
# 自动检测并生成 / Auto-detect and generate
cd my-node-project
acorn

# 指定模板和自定义变量 / Template with custom variables
acorn --template python-fastapi --var port=8080 --var app_name=myservice

# 交互式模式 / Interactive mode
acorn --interactive

# 预览不执行 / Dry run to preview changes
acorn --dry-run

# 强制覆盖 / Force overwrite
acorn --force

# 安全扫描 / Security scan
acorn --scan ./my-template

# 搜索和安装社区模板 / Search and install community templates
acorn --search fastapi
acorn --install SilasFu/init-template-fastapi

# 导出和导入配置 / Export and import project config
acorn --export my-config.yaml
acorn --import my-config.yaml

# 中文模式 / Chinese language mode
acorn --lang zh
```

---

## Project Config / 项目配置

创建项目级配置来锁定模板 / Lock template selection for a project:

```bash
acorn --init --template python-fastapi
```

这会在项目中创建 `.acorn/config.yaml`，后续运行将自动使用该模板。

This creates `.acorn/config.yaml` in the project directory. The template will be used automatically on subsequent runs.

---

## Templates / 模板

### 内置模板 / Built-in Templates

| 模板 / Template | 说明 / Description |
|----------------|-------------------|
| `node-api` | Node.js Express API |
| `python-fastapi` | Python FastAPI service |
| `react-vite` | React + Vite frontend |
| `golang-gin` | Go Gin web framework |
| `java-spring` | Java Spring Boot |
| `ruby-rails` | Ruby on Rails |
| `php-laravel` | PHP Laravel |
| `deno-app` | Deno application |
| `bun-app` | Bun application |
| `rust-app` | Rust application (via cargo) |

### 模板开发 / Template Development

模板通过 `template.yaml` 定义 / Templates are defined with a `template.yaml`:

```yaml
name: my-template
description: 我的自定义模板 / My custom template
version: 1.0.0
type: python
files:
  - Dockerfile
  - docker-compose.yml
  - .env.example
variables:
  - name: port
    default: "8000"
    prompt: "应用端口 / Application port"
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

模板文件放在 `files/` 子目录中，支持 Jinja2 模板语法。

Template files go in the `files/` subdirectory, supporting Jinja2 template syntax.

---

## Configuration / 配置文件

全局配置 / Global config: `~/.acorn/config.yaml`

```yaml
default_lang: en
log_level: INFO
offline: false
```

---

## Extending / 扩展

### 插件 / Plugins

Python 插件放在 `~/.config/acorn/plugins/`:

Place Python plugins in `~/.config/acorn/plugins/`:

```python
def before_detect(context):
    # 修改检测上下文 / Modify detection context
    return context

def after_generate(context):
    # 生成后钩子 / Post-generation hook
    return context
```

### 自定义命令 / Custom Commands

可执行脚本放在 `~/.config/acorn/commands/`，会自动注册为 CLI 子命令。

Place executable scripts in `~/.config/acorn/commands/` — they are automatically registered as CLI commands.

---

## Detection / 项目检测

Acorn 内置了以下语言的检测规则 / Built-in detection rules:

| 语言 / Language | 检测文件 / Detection Files |
|----------------|--------------------------|
| **Node.js** | `package.json`, `index.js`, `app.js`, `server.js` |
| **Python** | `requirements.txt`, `pyproject.toml`, `setup.py`, `main.py`, `app.py` |
| **Go** | `go.mod`, `main.go` |
| **Java** | `pom.xml`, `build.gradle`, `pom.xml` |
| **Ruby** | `Gemfile`, `Gemfile.lock` |
| **PHP** | `composer.json`, `index.php` |
| **Rust** | `Cargo.toml`, `main.rs` |
| **Deno** | `deno.json`, `deno.jsonc`, `main.ts`, `main.js` |
| **Bun** | `bun.lockb`, `bunfig.toml` |

---

## Auto-generation / 自动生成

当没有匹配模板时，Acorn 会根据项目类型自动生成以下文件：

When no template matches, Acorn auto-generates these files based on project type:

| 文件 / File | 说明 / Description |
|------------|-------------------|
| `Dockerfile` | 多阶段 Docker 构建 / Multi-stage Docker build |
| `docker-compose.yml` | Docker Compose 配置 / Docker Compose config |
| `.gitignore` | 按语言优化的 .gitignore / Language-optimized .gitignore |
| `.devcontainer/devcontainer.json` | VS Code Dev Container 配置 |
| `Makefile` | 常用命令快捷方式 / Common command shortcuts |
| `.nvmrc` | Node.js 版本锁定（仅 Node）/ Node version pinning (Node only) |
| `.env.example` | 环境变量示例 / Environment variable example |

---

## License / 许可证

MIT
