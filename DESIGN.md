# Acorn 升级方案设计

基于对非专业 AI 编程群体需求的分析，制定以下升级路线。

---

## 阶段一：降低门槛（MVP）

### 1.1 零门槛安装

**目标**：用户不需要懂 Python、虚拟环境，一行命令装完。

```bash
# 优先实现
brew install acorn

# 备选
curl -fsSL https://acorn.dev/install.sh | bash

# Windows
winget install acorn
```

**方案**：用 PyInstaller 或 Nuitka 打包成单文件二进制，发布到 GitHub Releases，Homebrew 维护一个 tap 或直接提 PR 进 core。

```yaml
# .github/workflows/release.yml
- name: Build binary
  run: |
    pip install pyinstaller
    pyinstaller --onefile --name acorn src/acorn/cli.py
- name: Upload to Release
  uses: actions/upload-release-asset@v1
```

**估算**：2-3 天（CI 配置 + 测试 + 发版流程）。

### 1.2 新手向导 `acorn wizard`

**目标**：零命令行知识也能用，一问一答完成项目初始化。

```
$ acorn wizard

👋 欢迎使用 Acorn！我来帮你初始化项目。

? 项目名称：my-app
? 项目类型：
  1) Web API 服务
  2) 前端应用
  3) 后端服务
  4) 全栈应用
  5) 不知道，你帮我选

? 技术栈偏好：
  ○ Node.js
  ○ Python
  ○ Go
  ○ Rust
  ○ Java
  ○ 都可以

? 需要 Docker 配置吗？ Yes
? 需要 CI/CD 吗？ Yes (GitHub Actions)
? 需要开发容器 (Dev Container) 吗？ Yes

✓ 正在生成项目...
✓ 已创建: my-app/
  ├── Dockerfile
  ├── docker-compose.yml
  ├── .env.example
  ├── .github/workflows/ci.yml
  └── .devcontainer/devcontainer.json

? 要用 VS Code / Cursor 打开吗？ Yes
```

**方案**：
- 新增 `acorn wizard` 子命令（或 `acorn --wizard`）
- 交互式问答，每一步都有默认值
- 问答结果映射到 `GenerationOptions`
- 最后自动执行 `acorn --dir <name> --template <detected> --force`

```python
# src/acorn/wizard.py
class WizardStep:
    prompt: str
    key: str
    options: list[WizardOption] | None  # None = 自由输入

class WizardFlow:
    steps: list[WizardStep]
    answers: dict[str, Any]

    def run(self) -> GenerationOptions:
        for step in self.steps:
            self.answers[step.key] = ask(step)
        return self.to_options()
```

**估算**：2-3 天。

### 1.3 首次运行自动进交互

**目标**：`acorn` 不带参数时不要只打印 usage，而是直接引导用户。

```python
# cli.py: main()
def main():
    if len(sys.argv) == 1:
        # 首次运行，自动进 wizard
        return cmd_wizard()
```

**估算**：0.5 天。

---

## 阶段二：AI 场景集成

### 2.1 生成 AI 上下文文件

**目标**：让 Acorn 初始化的项目天然适配 AI 编程工具。

```
my-app/
  ├── .cursorrules          # Cursor AI 行为规则
  ├── .clinerules            # Claude Code 行为规则  
  ├── AGENTS.md              # AI 代理操作手册（已实现雏形）
  └── CONTEXT.md             # 项目上下文摘要
```

`.cursorrules` 示例：

```markdown
You are an expert in Node.js/Express.

## Tech Stack
- Runtime: Node.js 20
- Framework: Express 4
- Testing: Jest
- Package Manager: npm

## Conventions
- Use CommonJS modules
- Error handling must use try/catch
- API routes in routes/ directory

## Project Structure
src/
  routes/    - API route handlers
  middleware/ - Express middleware
  models/    - Data models
```

**方案**：
- 模板新增 `ai_context` 字段
- 在 `template.yaml` 中配置 AI 上下文信息
- 生成时自动渲染 `.cursorrules`、`AGENTS.md` 等

```yaml
# template.yaml
name: node-api
ai_context:
  cursor_rules:
    tech_stack: "Node.js 20, Express 4, Jest"
    conventions:
      - "Use CommonJS modules"
      - "Error handling with try/catch"
    project_structure:
      src/routes/: "API route handlers"
      src/middleware/: "Express middleware"
```

**估算**：2 天。

### 2.2 AI 辅助检测

**目标**：让 AI 分析项目结构并推荐最优模板。

**方案**：
- 新增 `acorn analyze` 命令
- 读取项目文件 + 调用 LLM（通过 `OPENAI_API_KEY` 环境变量）
- AI 分析后返回推荐的模板、变量值、项目结构建议

```bash
acorn analyze .
```

```
🔍 分析项目 /my-app...

  Detected: Node.js project (Express, Jest, TypeScript)
  Recommended template: node-api (confidence: 92%)
  Suggested: --var port=3000 --var node_version=20

  💡 检测到 TypeScript 配置，需要 --template node-api-ts 吗？
```

**方案**：
- LLM 调用作为可选依赖 `acorn[ai]`
- 提示词工程：传入项目文件列表 + 现有检测结果
- AI 返回 JSON 格式的结构化建议

```python
# src/acorn/analyzer.py
def analyze_with_ai(dir_path: Path, detection: DetectionResult) -> AISuggestion:
    files = [str(f.relative_to(dir_path)) for f in dir_path.rglob("*") if f.is_file()]
    prompt = f"""
    Project files: {files}
    Detection result: {detection.model_dump_json()}
    Suggest: template, variables, project_structure_improvements
    """
    response = call_llm(prompt)
    return AISuggestion.model_validate_json(response)
```

**估算**：3 天。

---

## 阶段三：救火命令

### 3.1 `acorn dockerize` — 给已有项目加 Docker 配置

**目标**：项目已经写了一半，发现缺 Docker 配置，不用从头初始化。

```bash
cd my-existing-project
acorn dockerize
```

```
🔍 检测到: Python (FastAPI)
  ✓ 已创建: Dockerfile
  ✓ 已创建: docker-compose.yml
  ✓ 已创建: .dockerignore
```

**方案**：
- 新增 `cmd_dockerize`，复用模板的 Dockerfile/docker-compose 生成逻辑
- 不覆盖已有文件（除非 `--force`）
- 自动检测项目类型选择合适的 Docker 模板

```python
def cmd_dockerize(args) -> int:
    result = detect_project_type(target_dir)
    template = load_templates(result.project_type)
    generate_files(template, target_dir, only=["Dockerfile", "docker-compose.yml", ".dockerignore"])
```

**估算**：1 天。

### 3.2 `acorn add-ci` — 补充 CI 配置

**目标**：一键添加 GitHub Actions / GitLab CI 配置。

```bash
acorn add-ci --provider github
```

```
✓ 已创建: .github/workflows/ci.yml
✓ 已创建: .github/workflows/deploy.yml
```

**方案**：
- 内置常用 CI 模板（GitHub Actions、GitLab CI）
- 根据项目类型自动选择测试命令、Node/Python 版本
- `--provider` 支持 `github`、`gitlab`、`circleci`

**估算**：1.5 天。

### 3.3 `acorn lint-init` — 一键加 lint/format 配置

```bash
acorn lint-init --tool eslint --format prettier
```

**估算**：1 天。

---

## 阶段四：社区与生态

### 4.1 模板市场改进

**目标**：从"能搜能用"变成"好用敢用"。

```
acorn search fastapi --stars 100
acorn install SilasFu/fastapi-starter --verify
```

- 社区模板质量评分（基于 GitHub stars / downloads）
- 模板验证机制（安装前自动检查 template.yaml 合法性）
- 模板使用统计（辅助判断流行度）

### 4.2 预设技术栈组合

**目标**：一句命令搞定完整技术栈。

```bash
acorn --stack nextjs-tailwind-shadcn
acorn --stack fastapi-sqlalchemy-react
acorn --stack go-grpc-postgres
```

每个 stack 映射到一个复合模板，包含：
- 基础配置（Docker、CI）
- 框架集成
- 目录结构约定
- AI 上下文文件

### 4.3 模板脚手架

允许社区用户快速创建和发布模板：

```bash
acorn template new my-template
acorn template publish my-template
```

---

## 阶段五：体验打磨

### 5.1 进度与反馈

- 生成文件时显示进度条
- 失败时给出可操作的修复建议（而非 stack trace）
- 生成完成后显示"下一步"指南

### 5.2 模板预览

```bash
acorn preview --template node-api
```

生成前在终端预览文件结构树 + 关键文件内容。

### 5.3 自动更新

- 后台检查新版本
- 提示更新并提供一键升级命令
- 发布前自动运行模板兼容性测试

---

## 实施优先级

| 阶段 | 功能 | 预估工期 | 影响面 |
|------|------|---------|--------|
| P0 | Homebrew 安装 + 单文件二进制 | 2-3 天 | 安装门槛 |
| P0 | `acorn wizard` 新手向导 | 2-3 天 | 新手体验 |
| P0 | 首次运行自动进交互 | 0.5 天 | 开箱体验 |
| P1 | 生成 `.cursorrules` 等 AI 上下文 | 2 天 | AI 编程场景 |
| P1 | `acorn dockerize` 救火命令 | 1 天 | 实用场景 |
| P1 | `acorn add-ci` | 1.5 天 | 实用场景 |
| P2 | AI 辅助分析 (`acorn analyze`) | 3 天 | 高级场景 |
| P2 | 预设技术栈组合 (`--stack`) | 2 天 | 模板生态 |
| P3 | 社区模板评分/验证 | 2 天 | 信任机制 |
| P3 | 进度条、预览、自动更新 | 3 天 | 体验打磨 |

P0 可以开始，其余按需逐步推进。
