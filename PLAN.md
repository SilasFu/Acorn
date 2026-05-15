# Phase 1 实施方案 v4（最终版）

> 基于原始战略建议、DESIGN.md、两次审核（共发现 15 个问题并修复）后的最终执行方案。
> 所有内置文件的生成路径统一为 `generators/builtin.py:generate_file_content()` 单一入口。
> Jinja2 仅用于用户自定义模板场景。

---

## 一、架构总览

### 核心数据流

```
用户命令                           生成路径
─────────────────────────────────────────────────
acorn (无参数)
  └─ cmd_doctor()
       ├─ diagnosis 展示
       └─ fix_all() ──────────────────┐
                                      │
acorn fix --ai                        │
acorn fix --dockerfile                │
acorn fix --all                       │
  └─ cmd_fix()                        │
       └─ fix_all / fix_individual ───┤
                                      │
acorn --dockerize                     │
  └─ cmd_dockerize() ─────────────────┤
                                      │
auto_generate() (无模板匹配兜底) ─────┤
                                      ▼
                              ┌────────────────────────┐
                              │ generators/builtin.py  │
                              │ - generate_file_content│ ← 唯一入口
                              │ - 内置 Dockerfile      │
                              │ - docker-compose.yml   │
                              │ - .dockerignore        │
                              │ - .gitignore           │
                              │ - .cursorrules         │
                              │ - CLAUDE.md            │
                              │ - copilot-instructions │
                              └────────────────────────┘

acorn --template xx ───→ template_engine.py (Jinja2 模板，用户自定义)
```

### 产品定位转变

```
Before:  智能项目初始化工具 — 自动检测项目类型、匹配模板、生成配置
After:   AI 编程环境优化器 — 让 Cursor/Claude Code/Copilot 更懂你的项目
```

### 版本与兼容性

| 项 | 值 |
|---|---|
| 新版本号 | `0.2.0`（当前 `0.1.0`） |
| Python 最低版本 | `>=3.10` |
| 新增运行时依赖 | `tomli>=2.0`（仅 3.10，通过 `optional-dependencies`） |
| 向后兼容 | CLI 参数全部保留，旧 import 路径全部转发 |
| 默认行为变更 | `acorn` 无参数从 wizard 改为 doctor（有代码时） |

---

## 二、最终目录结构

```
src/acorn/
├── cli.py                        # ~180 行，纯路由 + 转发导入
├── format.py                     # ~40 行，共享工具（color, confirm, exit codes）
├── _compat.py                    # tomllib 兼容层
│
├── commands/
│   ├── __init__.py
│   ├── doctor.py                 # cmd_doctor() ~120 行
│   ├── fix.py                    # cmd_fix() + fix_all() ~150 行
│   ├── generate.py               # cmd_generate() 从旧 cli.py 移出
│   ├── docker.py                 # cmd_dockerize() + cmd_add_ci() ~80 行
│   ├── analyze_cmd.py            # cmd_analyze() 从旧 cli.py 移出
│   ├── clean.py                  # cmd_clean() 从旧 cli.py 移出
│   ├── template_cmd.py           # cmd_list/add/remove/init/validate
│   ├── marketplace.py            # cmd_search/install
│   └── admin.py                  # cmd_completion/export/import/check_update
│
├── analysis/
│   ├── __init__.py
│   ├── detector.py               # 从根目录移入（原 detector.py 实现）
│   ├── insights.py               # 确定性项目分析 ~200 行
│   ├── health.py                 # HealthReport + diagnose() ~100 行
│   └── health_rules.py           # CheckRule 定义 ~50 行
│
├── generators/
│   ├── __init__.py
│   └── builtin.py                # 统一生成器 ~400 行（核心新增）
│
├── detector.py                   # 转发 → analysis.detector
├── template_engine.py            # 保留：渲染引擎 + auto_generate + generate_from_template
├── wizard.py                     # 保留：import 改为 from commands.generate
├── models.py                     # 不变
├── i18n.py                       # 不变
├── config.py                     # 不变
├── locales/                      # 不变，追加 key
├── templates/                    # 不变
├── detectors/                    # 不变
└── ...（其余文件不变）
```

---

## 三、新增文件详解

### 3.1 `src/acorn/format.py` — 共享工具

依赖：无。从 `cli.py` 拆出。

```python
import sys

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_NO_MATCH = 2

COLORS = {
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}

def color(text: str, code: str) -> str:
    c = COLORS.get(code, "")
    return f"{c}{text}{COLORS['reset']}"

def suggest_help() -> str:
    return color(" (use --help for usage)", "dim")

def confirm_or_exit(prompt_text: str, default_yes: bool = True) -> bool:
    default = "Y/n" if default_yes else "y/N"
    try:
        choice = input(f"{color('?', 'blue')} {prompt_text} [{default}]: ").strip().lower()
        if default_yes:
            return choice not in ("n", "no")
        return choice in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
```

### 3.2 `src/acorn/_compat.py` — Python 版本兼容

```python
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore[assignment]

__all__ = ["tomllib"]
```

### 3.3 `src/acorn/analysis/insights.py` — 确定性分析

数据模型：

```python
@dataclass
class ProjectInsights:
    language: str = "unknown"              # "node" | "python" | "go" | ...
    framework: str | None = None           # "next.js" | "express" | "fastapi" | ...
    package_manager: str | None = None     # "npm" | "yarn" | "pnpm"

    has_src_dir: bool = False
    has_app_router: bool = False
    src_structure: dict[str, list[str]] = field(default_factory=dict)
    api_route_paths: list[str] = field(default_factory=list)
    api_route_detection_method: str = "none"  # "nextjs-app-router" | "none"

    key_dependencies: dict[str, str] = field(default_factory=dict)

    bundler: str | None = None
    css_framework: str | None = None
    orm: str | None = None
    test_runner: str | None = None
    auth_lib: str | None = None

    entry_points: list[str] = field(default_factory=list)
```

核心函数：

```python
def analyze(dir_path: Path) -> ProjectInsights:
    """全确定性分析 — 无 AST，只读文件和依赖"""
    ins = ProjectInsights()

    pkg = _read_json_safe(dir_path / "package.json")
    if pkg:
        ins.language = "node"
        _analyze_js_deps(ins, pkg)
        _analyze_js_structure(ins, dir_path, pkg)

    pyproj = _read_toml_safe(dir_path / "pyproject.toml")
    if pyproj and ins.language == "unknown":
        ins.language = "python"
        _analyze_py_deps(ins, pyproj)
    elif (dir_path / "requirements.txt").exists() and ins.language == "unknown":
        ins.language = "python"

    if (dir_path / "go.mod").exists() and ins.language == "unknown":
        ins.language = "go"
    if (dir_path / "Cargo.toml").exists() and ins.language == "unknown":
        ins.language = "rust"
    # Java / Ruby / PHP / Deno / Bun 同理

    ins.has_src_dir = (dir_path / "src").is_dir()
    if ins.has_src_dir:
        _analyze_src_structure(ins, dir_path)

    return ins
```

`has_source_code()` 辅助函数：

```python
SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php", ".c", ".cpp", ".h", ".hpp"}
IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "target", "build", "dist", ".next", ".nuxt", ".idea", ".vscode", "vendor"}

def has_source_code(dir_path: Path) -> bool:
    try:
        for f in dir_path.rglob("*"):
            if any(part in IGNORE_DIRS for part in f.relative_to(dir_path).parts):
                continue
            if f.is_file() and f.suffix in SOURCE_EXTENSIONS:
                return True
    except PermissionError:
        return False
    return False
```

### 3.4 `src/acorn/analysis/health.py` + `health_rules.py` — 健康检查

数据模型：

```python
class CheckCategory(str, Enum):
    AI_READINESS = "ai_readiness"
    DEVOPS = "devops"
    CODE_QUALITY = "code_quality"

class CheckPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class HealthCheck:
    category: CheckCategory
    name: str
    status: bool                   # True = OK
    message_key: str               # i18n key
    fix_target: str | None         # 传给 fix.py 的 target 名
    priority: CheckPriority
    auto_fixable: bool
    detail: str | None = None

@dataclass
class HealthReport:
    project_path: Path
    project_type: str
    framework: str | None
    confidence: float
    checks: list[HealthCheck]
    summary: dict[str, int]

    def to_dict(self) -> dict:
        return {
            "project": str(self.project_path),
            "type": self.project_type,
            "framework": self.framework,
            "confidence": self.confidence,
            "summary": self.summary,
            "checks": [
                {
                    "category": c.category.value,
                    "name": c.name,
                    "status": c.status,
                    "message_key": c.message_key,
                    "auto_fixable": c.auto_fixable,
                }
                for c in self.checks
            ],
        }
```

`health_rules.py` 中定义的检查项：

```python
AI_CHECKS = [
    CheckRule(AI_READINESS,    ".cursorrules",             "cursorrules",  HIGH,   True,  ".cursorrules"),
    CheckRule(AI_READINESS,    "CLAUDE.md",                "claude-md",    HIGH,   True,  "CLAUDE.md"),
    CheckRule(AI_READINESS,    ".github/copilot-instructions.md", "copilot", MEDIUM, True, ".github/copilot-instructions.md"),
]
DEVOPS_CHECKS = [
    CheckRule(DEVOPS,          "Dockerfile",               "dockerfile",   MEDIUM, True,  "Dockerfile"),
    CheckRule(DEVOPS,          ".dockerignore",            "dockerignore", MEDIUM, True,  ".dockerignore"),
    CheckRule(DEVOPS,          ".github/workflows/ci.yml", None,           LOW,    False, ".github/workflows/ci.yml"),
]
QUALITY_CHECKS = [
    CheckRule(CODE_QUALITY,    ".gitignore",               "gitignore",    HIGH,   True,  ".gitignore"),
]
```

### 3.5 `src/acorn/generators/builtin.py` — 统一生成器（核心）

这是整个方案最关键的单一文件。所有内置文件生成只有这一条路径。

```python
FILE_TYPES = {
    "Dockerfile",
    "docker-compose.yml",
    ".dockerignore",
    ".gitignore",
    ".cursorrules",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
}

def generate_file_content(
    file_type: str,
    project_type: str,
    variables: dict[str, str] | None = None,
    insights=None,
    detection=None,
) -> str:
    """统一入口：生成指定文件内容"""
```

包含的子生成器：
- `_generate_dockerfile(project_type, variables)` — 9 种语言多阶段构建
- `_generate_docker_compose(project_type, variables)` — 按语言设环境变量，删除 `version:`
- `_generate_dockerignore(project_type, variables)` — 按语言
- `_generate_gitignore(project_type, variables)` — 按语言
- `_generate_cursorrules(project_type, variables, insights, detection)` — 结构化 Markdown
- `_generate_claude_md(project_type, variables, insights, detection)` — Anthropic 格式
- `_generate_copilot_instructions(project_type, variables, insights, detection)` — GitHub 格式

包含的 9 种语言约定表：`LANGUAGE_CONVENTIONS`、`ANTI_PATTERNS`、`COMMON_COMMANDS`、`ENV_VARS`、`DOCKER_IGNORES`、`GIT_IGNORES`。

### 3.6 `src/acorn/commands/doctor.py` — 医生命令

核心逻辑：

```
cmd_doctor()
  ├─ has_source_code(cwd) == False → cmd_wizard()
  ├─ diagnosis = diagnose(cwd)
  ├─ _display_report(diagnosis)     ← 双语 + color 输出
  ├─ maybe_prompt()                 ← Telemetry 弹窗延迟至此
  └─ 有失败项 → 询问用户 → fix_all(cwd, detection, insights)
```

`_display_report()` 输出格式：

```
🔍 Acorn 项目报告 — my-project
  类型: node (置信度: 95%)

  🤖 AI 就绪
    ✗ .cursorrules                         缺失，AI 无法了解项目约定
      [acorn fix --cursorrules]
    ✗ CLAUDE.md                            缺失
      [acorn fix --claude-md]

  🐳 DevOps
    ✓ Dockerfile                           已存在

  📋 代码质量
    ✓ .gitignore                           已存在

  ════════════════════════════════════════
  ✓ 3 passed  ✗ 2 failed

? 要修复所有可自动修复的问题吗？ [Y/n]:
```

### 3.7 `src/acorn/commands/fix.py` — 修复命令

文件型修复统一映射：

```python
GENERATABLE_FILES = {
    "dockerfile":    {"file_type": "Dockerfile",          "dest_name": "Dockerfile"},
    "dockerignore":  {"file_type": ".dockerignore",       "dest_name": ".dockerignore"},
    "gitignore":     {"file_type": ".gitignore",          "dest_name": ".gitignore"},
    "cursorrules":   {"file_type": ".cursorrules",        "dest_name": ".cursorrules"},
    "claude-md":     {"file_type": "CLAUDE.md",           "dest_name": "CLAUDE.md"},
    "copilot":       {"file_type": ".github/copilot-instructions.md", "dest_name": ".github/copilot-instructions.md"},
}
```

所有 `cmd_fix_individual()` 都走 `generate_file_content()`，传入统一的 `detection` 和 `insights` 避免重复扫描。

### 3.8 `src/acorn/commands/docker.py` — Docker 命令

`cmd_dockerize()` 不再依赖模板引擎，直接调 `generate_file_content()`。

### 3.9 `cli.py` 精简版

- `build_parser()` 保留所有现有参数 + 新增 `fix` 参数组
- `main()` 纯路由分发
- 保留所有 `cmd_*` 的转发导入（保持旧 `from acorn.cli import cmd_*` 可用）
- 子命令 rewrite：`sys.argv[1] == "fix"` → `--fix`，`sys.argv[1] == "wizard"` → `--wizard`

---

## 四、修改文件详解

### 4.1 `src/acorn/detector.py` → 转发

```python
# 删除所有实现代码
from acorn.analysis.detector import *  # noqa: F401, F403
```

实现移至 `src/acorn/analysis/detector.py`。

### 4.2 `src/acorn/template_engine.py` — 清洗

删除以下函数（已被 `builtin.py` 替代）：
- `_generate_dockerfile()`
- `_generate_docker_compose()`
- `_generate_gitignore()`
- `_generate_dockerignore()`
- `_generate_cursorrules()`
- `DOCKER_FILES` 常量

`auto_generate()` 改为调用 `builtin.generate_file_content()`。
`generate_from_template()` 末尾不再调 `_generate_cursorrules()`（已由 `builtin` 统一处理）。

### 4.3 `src/acorn/wizard.py` — import 修复

```diff
- from acorn.cli import build_parser, cmd_generate
+ from acorn.cli import build_parser
+ from acorn.commands.generate import cmd_generate
+ from acorn.format import color
```

### 4.4 `pyproject.toml` — 版本号

```diff
- version = "0.1.0"
+ version = "0.2.0"

+ [project.optional-dependencies]
+ advanced = ["jinja2", "tomli>=2.0"]
```

### 4.5 `src/acorn/locales/zh.yaml` — 追加

```yaml
messages:
  doctor_title: "🔍 Acorn 项目报告 — {{project}}"
  project_type: "类型: {{type}} (置信度: {{confidence}})"
  ai_readiness: "🤖 AI 就绪"
  devops: "🐳 DevOps"
  code_quality: "📋 代码质量"
  passed: "通过"
  failed: "失败"
  fix_prompt: "要修复所有可自动修复的问题吗？"

  check_.cursorrules_present: "已存在"
  check_.cursorrules_absent: "缺失，AI 无法了解项目约定"
  check_CLAUDE.md_present: "已存在"
  check_CLAUDE.md_absent: "缺失"
  check_.github/copilot-instructions.md_present: "已存在"
  check_.github/copilot-instructions.md_absent: "缺失"
  check_Dockerfile_present: "已存在"
  check_Dockerfile_absent: "缺失"
  check_.dockerignore_present: "已存在"
  check_.dockerignore_absent: "缺失"
  check_.gitignore_present: "已存在"
  check_.gitignore_absent: "缺失"

  fix_generating: "正在生成 {{name}}..."
  fix_generated: "已生成 {{name}}"
  fix_skipped: "跳过 {{name}} (已存在)"
  fix_all_done: "修复完成"
  fix_nothing: "没有需要修复的问题"

  language_node: "Node.js"
  language_python: "Python"
  language_go: "Go"
  language_rust: "Rust"
  language_java: "Java"
  language_ruby: "Ruby"
  language_php: "PHP"
  language_deno: "Deno"
  language_bun: "Bun"
```

### 4.6 `src/acorn/locales/en.yaml` — 追加

与 `zh.yaml` 结构完全对应，值用英文。

---

## 五、删除文件

| 文件 | 原因 |
|------|------|
| `src/acorn/generators/docker_tpl.py` | 功能被 `builtin.py` 完全覆盖 |
| `src/acorn/generators/ai_context.py` | 功能被 `builtin.py` 完全覆盖 |

---

## 六、测试计划

### 新增测试文件（11 个，~48 个测试）

| 文件 | 测试数 | 覆盖内容 |
|------|--------|---------|
| `tests/test_insights.py` | 10 | 9 种语言检测、API 路由、空项目、排除目录 |
| `tests/test_health.py` | 7 | 全检查通过/部分缺失/全部缺失、has_source_code、排除 Acorn 自身 |
| `tests/test_doctor.py` | 4 | 输出格式、wizard fallback、--json、英文/中文 |
| `tests/test_builtin.py` | 12 | 9 种语言 Dockerfile 多阶段、docker-compose 无 version、.dockerignore、.gitignore 内容正确性 |
| `tests/test_ai_context.py` | 8 | 3 种格式生成、内容包含关键字段、force/dry-run/skip |
| `tests/test_fix.py` | 6 | 单项修复、批量修复、跳过已存在、--ai 一次性生成 3 个、检测结果复用 |
| `tests/test_cli_refactored.py` | 3 | 路由正确性、转发导入、子命令 rewrite |
| `tests/test_docker.py` | 2 | `--dockerize` 与 `fix --dockerfile` 输出一致 |

### 测试原则

- 所有文件操作用 `tmp_path` 隔离
- 不接触真实文件系统
- 不依赖网络
- `detect_project_type` 测试依赖 fixtures 目录（已有）

---

## 七、执行顺序（9 天）

```
Day 1  Step 0: 创建 _compat.py + format.py + 空包目录
       Step 1: 代码重构
         - analysis/detector.py 移入实现，detector.py 改为转发
         - 9 个 commands/ 文件创建，cli.py 精简
         - wizard.py import 修复
         - template_engine.py 清洗
         - pyproject.toml 版本号
       → pytest tests/ 全部通过

Day 2  Step 2: analysis/insights.py
         - 完整 analyze() 实现
         - 9 种语言框架检测
         - API 路由检测
         - has_source_code()
       → test_insights.py 全部通过

Day 3  Step 3: analysis/health.py + health_rules.py + commands/doctor.py
         - HealthCheck 模型 + 检查规则
         - diagnose() + _display_report()
         - Telemetry 弹窗延迟
       → test_health.py + test_doctor.py 全部通过

Day 4  Step 4: generators/builtin.py
         - generate_file_content() 统一入口
         - 9 种语言 Dockerfile (多阶段)
         - docker-compose.yml、.dockerignore、.gitignore
         - .cursorrules、CLAUDE.md、copilot-instructions.md
         - 9 种语言约定表
       → 删除 generators/docker_tpl.py + generators/ai_context.py
       → test_builtin.py + test_ai_context.py 全部通过

Day 5  Step 5a: commands/fix.py
         - cmd_fix() / fix_all() / cmd_fix_individual()
         - 统一走 generate_file_content()
         - 一次 scan 复用 detection/insights
       → test_fix.py 全部通过

Day 6  Step 5b: 集成联调
         - doctor → fix --all 全流程
         - fix --dockerfile vs --dockerize 输出一致
         - fix --cursorrules vs --template node-api 不冲突
       → 手动 + diff 验证

Day 7  Step 6: commands/docker.py 改用 builtin
         - cmd_dockerize() 删除模板引擎依赖
         - auto_generate() 改用 generate_file_content()
         - 路径引用统一 /tmp → tempfile
       → test_docker.py 全部通过

Day 8  Step 7: i18n + README + Homebrew + CI
         - locales/zh.yaml + en.yaml 追加
         - README 新故事线
         - release.yml 更新
         - Formula/acorn.rb 更新

Day 9  缓冲
         - 覆盖率 ≥ 80%
         - 冒烟测试全过
         - git tag v0.2.0
```

---

## 八、验收条件（19 项）

| # | 验收项 | 验证方式 | Step |
|---|--------|---------|------|
| 1 | `pytest tests/` 全部通过 | pytest | 1 |
| 2 | `acorn`（有代码目录）→ doctor 报告 | 手动 | 3 |
| 3 | `acorn`（空目录）→ wizard | 手动 | 3 |
| 4 | `acorn --json` → JSON 报告 | 手动 + json.tool | 3 |
| 5 | `acorn fix --ai` → 生成 3 个 AI 文件 | 手动 | 5 |
| 6 | `acorn fix --cursorrules` → 仅 .cursorrules | 手动 | 5 |
| 7 | `acorn fix --dockerfile` → Dockerfile | 手动 | 5 |
| 8 | `acorn fix --dockerignore` → .dockerignore | 手动 | 5 |
| 9 | `acorn fix --gitignore` → .gitignore | 手动 | 5 |
| 10 | `acorn --dockerize` → 3 个 Docker 文件 | 手动 | 6 |
| 11 | `acorn fix --dockerfile` 和 `acorn --dockerize` 输出一致 | diff 对比 | 6 |
| 12 | `acorn --template node-api` → 正常生成（Jinja2 模板） | 手动 | 1 |
| 13 | `acorn --list` → 列出模板 | 手动 | 1 |
| 14 | `acorn --lang zh` → 中文显示 | 手动 | 7 |
| 15 | `from acorn.cli import cmd_generate` 无错误 | `python -c` | 1 |
| 16 | `from acorn.detector import detect_project_type` 无错误 | `python -c` | 1 |
| 17 | `from acorn.generators.builtin import generate_file_content` 无错误 | `python -c` | 4 |
| 18 | 覆盖率 `pytest --cov=src/acorn` ≥ 80% | pytest | 9 |
| 19 | `brew install acorn/tap/acorn` 成功 | CI 运行 | 7 |

---

## 九、审核修复总表

| # | 问题 | 严重度 | v4 修复方式 |
|---|------|--------|------------|
| 1 | 循环导入 | 🔴 阻塞 | `format.py` 共享模块 |
| 2 | `--all` 歧义 | 🔴 阻塞 | 移除 `--fix --all`，只用 `acorn fix --all` |
| 3 | i18n key 前缀不匹配 | 🔴 阻塞 | 所有 key 嵌套在 `messages.` 下 |
| 4 | 重复分析 3 次 | 🟡 重要 | fix_all 接受 detection/insights 参数复用 |
| 5 | PyInstaller 漏 import | 🟡 重要 | `--hidden-import acorn.json_output` |
| 6 | Telemetry 弹窗时机 | 🟡 重要 | 延迟到 doctor 报告后 |
| 7 | Python 3.10 tomllib | 🟡 重要 | try-import tomli，pyproject 加入 optional-dep |
| 8 | has_source_code 误判 | 🟡 重要 | 检查文件后缀 + IGNORE_DIRS 排除 |
| 9 | 语言覆盖不全 | 🟢 改进 | 9 种语言完整约定表 |
| 10 | alpine:latest | 🟢 改进 | alpine:3.19 锁定 |
| 11 | NODE_ENV 误写 | 🟢 改进 | 按 project_type 设置 |
| 12 | API 路由检测标记 | 🟢 改进 | api_route_detection_method 字段 |
| 13 | 缺少 --json 支持 | 🟢 改进 | to_dict() + json 输出 |
| 14 | 缺少 fix 子命令 | 🟢 改进 | sys.argv rewrite |
| 15 | analysis/detector 缺失 | 🔴 阻塞 | Step 1 新增移植子任务 |
| 16 | template_engine 与 ai_context 冲突 | 🔴 阻塞 | 删除旧 _generate_cursorrules |
| 17 | wizard.py import 断裂 | 🔴 阻塞 | 改 import 路径 |
| 18 | --fix --dockerfile 与 --dockerize 双实现 | 🔴 阻塞 | 两者都走 generate_file_content |
| 19 | doctor _fix_all 数据断层 | 🟡 重要 | fix_all 接受 detection/insights |
| 20 | --ai/--devops/--quality 未注册 | 🔴 阻塞 | build_parser 新增参数 |
| 21 | cli.py 缺少转发导入 | 🟡 重要 | cli.py 顶部统一 import |
| 22 | fix_all 函数名混乱 | 🟡 重要 | 唯一实现在 fix.py |
| 23 | 版本号未更新 | 🟡 重要 | pyproject.toml → 0.2.0 |
| 24 | i18n key 风格不一致 | 🟡 重要 | messages.check_ 统一 |
| 25 | tomli 未加入依赖 | 🟡 重要 | pyproject.toml optional-dependencies |
| 26 | format.py 引用替换 | 🟢 改进 | Step 1 检查清单 |
