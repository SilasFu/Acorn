# Acorn

AI 编码环境优化工具 — 自动检测项目、诊断缺失配置、一键修复。

AI coding environment optimizer — auto-detect, diagnose, and fix your project setup.

---

## 新能力 / What's New

```bash
# 一键诊断 + 修复 / Diagnose & fix in one go
cd my-project
acorn

# 诊断模式 — 查看项目健康状态 / Check project health
acorn --json          # JSON 输出供脚本使用

# 自定义修复 / Targeted fixes
acorn fix --dockerfile           # 只生成 Dockerfile
acorn fix --docker-compose       # 只生成 docker-compose.yml
acorn fix --dockerignore         # 只生成 .dockerignore
acorn fix --gitignore            # 只生成 .gitignore
acorn fix --cursorrules          # 只生成 Cursor AI 规则
acorn fix --claude-md            # 只生成 CLAUDE.md
acorn fix --copilot              # 只生成 Copilot 指令
acorn fix --ai                   # 生成所有 AI 配置文件
acorn fix --all                  # 全部修复

# 兼容旧用法 / Legacy shortcut
acorn --dockerize     # 等价于 acorn fix --dockerfile
```

支持 9 种语言 / Supports 9 languages:

| 语言 | 检测文件 | Docker 基础镜像 |
|------|----------|----------------|
| Node.js | `package.json`, `index.js` | `node:20-alpine` |
| Python | `requirements.txt`, `pyproject.toml` | `python:3.12-slim` |
| Go | `go.mod`, `main.go` | `golang:1.22-alpine` |
| Rust | `Cargo.toml`, `main.rs` | `rust:1.78-slim` |
| Java | `pom.xml`, `build.gradle` | `eclipse-temurin:21-jdk` |
| Ruby | `Gemfile`, `Gemfile.lock` | `ruby:3.3-alpine` |
| PHP | `composer.json`, `index.php` | `php:8.3-cli` |
| Deno | `deno.json`, `deno.jsonc` | `denoland/deno:latest` |
| Bun | `bun.lockb`, `bunfig.toml` | `oven/bun:latest` |

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
# 进入项目目录，自动诊断
cd my-node-project
acorn
# → 诊断报告 + 提示是否自动修复

# 指定目标目录
acorn --dir /path/to/project

# 中文模式
acorn --lang zh

# 预览不执行
acorn --dry-run
```

---

## Usage / 使用说明

### 诊断 / Doctor

`acorn` (无参数) = 诊断模式。检测 7 项检查：

| 检查项 | 类别 | 说明 |
|--------|------|------|
| `.gitignore` | DevOps | Git 忽略规则 |
| `Dockerfile` | DevOps | 容器化配置 |
| `docker-compose.yml` | DevOps | 本地开发编排 |
| `.cursorrules` | AI 就绪 | Cursor AI 项目规则 |
| `CLAUDE.md` | AI 就绪 | Claude Code 上下文 |
| `.github/copilot-instructions.md` | AI 就绪 | GitHub Copilot 指令 |
| `.editorconfig` | 代码质量 | 编辑器统一配置 |

### 修复 / Fix

```bash
# 子命令模式
acorn fix --dockerfile
acorn fix --ai
acorn fix --all --force    # 强制覆盖已有文件
acorn fix --all --dry-run  # 预览

# 或通过无参数诊断后的交互提示自动修复
acorn
```

### 生成 / Generate

```bash
# 从模板生成项目配置
acorn --template python-fastapi

# 交互式选择
acorn --interactive

# 组合多个模板
acorn --with node-api,react-vite

# 列出可用模板
acorn --list
```

### 向导 / Wizard

```bash
acorn --wizard
# 或：空目录下直接 acorn 会自动启动向导
```

---

## Examples / 示例

```bash
# 进入 Python 项目，自动诊断
cd my-python-app
acorn
# → 诊断报告：
#   ✓ .gitignore    已存在
#   ✗ Dockerfile    [acorn fix --dockerfile]
#   ✗ .cursorrules  [acorn fix --cursorrules]
#   是否修复所有可修复项？[Y/n]

# 指定语言修复
cd go-project
acorn fix --dockerfile --gitignore --force

# JSON 输出
acorn --json
# → {"project": "/path", "type": "node", "checks": [...], "summary": {...}}

# 中文模式
acorn --lang zh
```

---

## Detection / 项目检测

| 语言 | 检测文件 |
|------|----------|
| **Node.js** | `package.json`, `index.js`, `app.js`, `server.js` |
| **Python** | `requirements.txt`, `pyproject.toml`, `setup.py`, `main.py`, `app.py` |
| **Go** | `go.mod`, `main.go` |
| **Java** | `pom.xml`, `build.gradle` |
| **Ruby** | `Gemfile`, `Gemfile.lock` |
| **PHP** | `composer.json`, `index.php` |
| **Rust** | `Cargo.toml`, `main.rs` |
| **Deno** | `deno.json`, `deno.jsonc`, `main.ts`, `main.js` |
| **Bun** | `bun.lockb`, `bunfig.toml` |

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

```python
def before_detect(context):
    return context

def after_generate(context):
    return context
```

### 自定义命令 / Custom Commands

可执行脚本放在 `~/.config/acorn/commands/`，自动注册为 CLI 子命令。

### 模板开发 / Template Development

```yaml
# template.yaml
name: my-template
description: Python FastAPI service
version: 1.0.0
type: python
files:
  - Dockerfile
  - docker-compose.yml
  - .env.example
```

---

## License / 许可证

MIT
