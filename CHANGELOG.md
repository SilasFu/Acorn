# Changelog / 更新日志

## [0.3.1] - 2026-05-16

- CI fix: use bash shell for PyInstaller on Windows. / CI 修复：Windows 构建使用 bash shell。
- CI fix: match any version in Homebrew formula sed. / CI 修复：Homebrew formula 版本替换支持正则。
- Homebrew formula: 0.2.0 → 0.1.0 placeholder for CI replacement. / Homebrew formula 占位符版本统一。

## [0.3.0] - 2026-05-15

- Phase 2: Deep AI context generation with 15+ analysis dimensions (import style, module system, naming convention, state management, styling approach, API style, architecture pattern, directory purposes). / 深度 AI 上下文生成，15+ 分析维度。
- Phase 2: Rich `.cursorrules`, `CLAUDE.md`, `copilot-instructions.md` with project structure, API routes, and tech stack details. / 富内容 AI 上下文文件，包含项目结构、API 路由和技术栈详情。
- Phase 2: `analysis/ast_lite.py` — regex-based code analysis engine. / 基于正则的代码分析引擎。
- Phase 3: `acorn sync` — detect and fix stale AI context files. / 检测并修复过时的 AI 上下文文件。
- Phase 3: `acorn sync --sync-hook` — install pre-commit git hook. / 安装 pre-commit git 钩子。

## [0.2.0] - 2026-05-15

- Phase 1: Pivot to AI coding environment optimizer. / 转型为 AI 编码环境优化器。
- `acorn doctor` — 7-check health report with auto-fix prompt. / 7 项健康检查 + 自动修复。
- `acorn fix` — targeted file generation (Dockerfile, AI files, gitignore, etc.). / 定向文件生成。
- Unified `generators/builtin.py` with 9-language conventions. / 统一内置生成器，9 种语言约定。
- `acorn` no-args → doctor (if source exists) or wizard (if empty). / 无参数行为变更。

## [0.1.0] - 2024-01-01

- Initial alpha release. / 初始 Alpha 版本。
- Automatic project type detection. / 自动检测项目类型。
- Template-based project scaffolding. / 基于模板的项目脚手架。
- Interactive and non-interactive modes. / 交互式和非交互式模式。
- Docker, devcontainer, Makefile, nvmrc generation. / 自动生成 Docker、devcontainer、Makefile、nvmrc 等配置。
- GitHub marketplace template search and install. / 从 GitHub 市场搜索和安装模板。
- Plugin system with custom commands and hooks. / 插件系统，支持自定义命令和钩子。
- Security scanning for generated files. / 生成文件的安全扫描。
- Internationalization (en/zh). / 国际化支持（英文/中文）。
