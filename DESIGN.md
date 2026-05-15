# Acorn 升级方案设计（修订版）

> 基于 CTO 视角审核后的修订版本。审核要点：商业逻辑、工程风险、后向兼容、测试策略、隐私合规。

---

## 总体原则

1. **P0 先交付，P1 验证，P2/P3 决策** — 不做"大爆炸式"发布，每阶段收集反馈再决定下一步。
2. **每项功能必须有退出条件** — 用户不想用了能清理干净，功能废弃了不影响现有项目。
3. **不承诺做不到的事** — 标注已知风险、平台限制、依赖条件。

---

## 阶段零：地基加固

在加新功能前，先修技术债。

### 0.1 PyInstaller 兼容性验证

**风险**：现有代码中使用了 `__file__`、`Path(__file__).parent`、动态 import，PyInstaller 打包后这些行为会变。

**行动**：
1. 扫描代码中所有文件路径引用
2. 用 `sys._MEIPASS` 判断是否在打包环境
3. 编写 `_resource_path()` 工具函数统一处理

```python
def _resource_path(relative: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent
    return base / relative
```

**验证方式**：在 CI 中加一个 PyInstaller 打包步骤，运行 smoke test（检测+生成+扫描全部走一遍）。

**估算**：1 天。

### 0.2 路径引用统一

`template_engine.py` 中多处硬编码 `/tmp/.init-template-*`，macOS 的 `/tmp` 是符号链接，不同平台行为不同。统一用 `tempfile.gettempdir()`。

**估算**：0.5 天。

### 0.3 测试基础设施

- Wizard 测试方案：输入序列模拟 + 输出断言（`capsys`）
- 救火命令测试方案：先创建项目 → 运行命令 → 验证生成文件
- AI 分析测试方案：mock LLM 调用，测试 fallback 路径

**估算**：1 天。

---

## 阶段一：降低门槛（P0）

### 1.1 二进制分发（Homebrew tap + CI 构建矩阵）

**目标**：`brew install acorn/tap/acorn` 一行装完。三平台（macOS arm64/amd64、Linux amd64、Windows amd64）。

**方案**：

```yaml
# .github/workflows/release.yml — 简化版
jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, macos-13, windows-latest]
    steps:
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install pyinstaller
      - run: pyinstaller --onefile --name acorn src/acorn/cli.py
      - uses: actions/upload-artifact@v4
        with: { name: acorn-${{ matrix.os }}, path: dist/acorn* }
```

**Homebrew tap 维护**：

```bash
# 用户安装
brew tap acorn/tap https://github.com/SilasFu/homebrew-acorn
brew install acorn

# tap 仓库单独维护，仅包含 formula 文件
# class Acorn < Formula
#   desc "..."
#   url "https://github.com/SilasFu/Acorn/releases/download/v0.2.0/acorn-macos-arm64.tar.gz"
#   ...
```

**不承诺**：不提 PR 进 homebrew-core（门槛：50 stars + 稳定 API + 有维护者）。等项目达标后再做。

**已知风险**：
- PyInstaller 对 `__file__` 路径的处理 — 已在 0.1 验证
- macOS 代码签名/notarization — 首次发布不做，后续迭代
- Windows 上可能被杀毒软件误报 — 需要申请 EV 证书

**估算**：3 天（含 0.1 兼容性验证）。

### 1.2 `acorn wizard` 新手向导

**定位**：`wizard` 是 `--interactive` 的升级版，面向第一次使用的用户。两者的关系：

| 入口 | 用户 | 特点 |
|------|------|------|
| `acorn`（无参数）| 首次用户 | 自动进入 wizard |
| `acorn wizard` | 新手 | 引导式、多步骤、中英文 |
| `acorn --interactive` | 老手 | 精简版，更快的选择 |
| `acorn --template x` | 确定需求的用户 | 跳过问答，直接生成 |

**架构**：

```python
# src/acorn/wizard.py
class WizardStep:
    key: str
    prompt: str            # 显示问题
    prompt_zh: str | None  # 中文版
    input_type: Literal["text", "select", "confirm"]
    options: list[WizardOption] | None
    default: Any
    validator: Callable | None  # 输入校验

class WizardFlow:
    steps: list[WizardStep]
    answers: dict[str, Any]
    current_step: int
    checkpoint: Path  # 保存进度，支持 Ctrl+C 恢复

    def run(self) -> WizardResult:
        self._load_checkpoint()  # 恢复上次进度
        for step in self.steps:
            if step.key in self.answers:
                continue  # 已填过的步骤跳过
            self.answers[step.key] = self._ask(step)
            self._save_checkpoint()
        self._clear_checkpoint()
        return WizardResult(...)
```

**中文支持**：wizard 的 `prompt_zh` 字段为 `None` 时自动 fallback 到 `prompt`。翻译文件集中在 `locales/zh.yaml`。

**错误恢复**：每步完成后保存 `~/.acorn/wizard-checkpoint.json`。用户 Ctrl+C 退出后重新运行 `acorn wizard` 时自动恢复。`acorn wizard --reset` 清除检查点从零开始。

**测试方案**：

```python
def test_wizard_complete_flow(tmp_path, monkeypatch, capsys):
    inputs = iter(["my-app", "1", "y", "y", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    result = run_wizard()
    assert result.name == "my-app"
    assert result.project_type == "node"
```

**估算**：3 天（含 0.3 测试基础设施）。

### 1.3 无参数自动进 wizard

```python
def main():
    if len(sys.argv) == 1:
        return cmd_wizard(argparse.Namespace())
```

**注意**：不破坏任何现有 flag。仅当 `len(sys.argv) == 1` 时走 wizard，否则完全保持现有行为。

**估算**：0.5 天。

---

## 阶段二：AI 场景集成（P1）

### 2.1 生成 AI 上下文文件

**范围收缩**：只做 `.cursorrules`，暂不做 `.clinerules`。原因：
- Cursor 用户群更大
- Claude Code 的规则格式仍在快速迭代
- `.clinerules` 标记为 planned，等生态稳定再跟进

**方案**：

```yaml
# template.yaml
name: node-api
ai_context:
  cursor_rules:
    tech_stack: "Node.js 20, Express 4, Jest"
    conventions:
      - "Use CommonJS modules"
      - "Error handling with try/catch"
```

模板生成时自动渲染 `.cursorrules`（位置在项目根目录）。已有的 `.cursorrules` 不会被覆盖，除非用户确认。

**维护责任**：模板作者维护自己的 `ai_context`。Acorn 项目提供一个验证工具 `acorn validate-ai-context`，检查模板的 AI 规则是否包含必要字段。

**版本管理**：`ai_context` 加入 template.yaml schema 版本号。升级大版本时自动迁移。

**验证方式**：先用 Cursor 打开一个 Acorn 生成的项目，实测 AI 回答质量是否提升。验证通过再推广到所有模板。

**估算**：2 天。

### 2.2 `acorn dockerize` — 补充 Docker 配置

**与现有功能的区别**：

| | `acorn --dir . --force` | `acorn dockerize` |
|---|---|---|
| 行为 | 检测 + 匹配模板 + 生成全部文件 | 只生成 Dockerfile 和 docker-compose.yml |
| 覆盖策略 | 全部覆盖（或全部跳过） | 只处理 Docker 相关文件，不影响现有代码 |
| 使用场景 | 新项目初始化 | 已有项目缺 Docker 配置 |

**方案**：

```python
DOCKER_FILES = {"Dockerfile", "docker-compose.yml", ".dockerignore"}

def cmd_dockerize(target_dir: Path) -> int:
    result = detect_project_type(target_dir)
    if result.project_type == ProjectType.UNKNOWN:
        log_error("Cannot detect project type")
        return EXIT_ERROR
    template = _find_best_template(result.project_type)
    return generate_files(template, target_dir, only=DOCKER_FILES)
```

**不承诺**：不生成 `.dockerignore` 以外的 Docker 相关文件。

**估算**：1 天。

### 2.3 `acorn add-ci` — 补充 CI 配置

**范围收缩**：只支持 GitHub Actions。GitLab CI、CircleCI 标记为 planned。

**方案**：
- 内置 GitHub Actions workflow 模板（ci.yml，deploy.yml 可选）
- 根据 project type 自动选择 Node/Python/Go 版本
- 生成的 workflow 引用主流 action 版本（`actions/checkout@v4`, `actions/setup-python@v5` 等）

**版本锁定策略**：生成的 workflow 中 action 版本用 `@v4` 这种 major version tag，不用具体版本号，减少维护频率。

**估算**：1 天。

---

## 阶段三：高阶功能（P2）

### 3.1 AI 辅助分析 `acorn analyze`

**架构重设计**（基于 CTO 审核意见）：

```python
# src/acorn/analyzer.py

def analyze(dir_path: Path, options: AnalyzeOptions) -> AnalysisResult:
    detection = detect_project_type(dir_path)

    if not options.allow_ai:
        return AnalysisResult(
            detection=detection,
            source="rule",  # 纯规则分析
        )

    # Step 1: 用户确认
    if not confirm("Use AI to analyze project? Files metadata will be sent to LLM."):
        return AnalysisResult(detection=detection, source="rule")

    # Step 2: 只传模糊匹配的部分，不传全量文件列表
    ambiguous = _get_ambiguous_matches(detection)
    if not ambiguous:
        return AnalysisResult(detection=detection, source="rule")

    # Step 3: 调用 LLM（支持 OpenAI / 本地模型）
    try:
        suggestion = _call_llm(build_prompt(ambiguous, dir_path.name))
        return AnalysisResult(detection=detection, ai_suggestion=suggestion, source="ai")
    except Exception as e:
        log_warning(f"AI analysis failed: {e}")  # 不暴露具体错误信息
        return AnalysisResult(detection=detection, source="rule")  # 静默降级
```

**安全设计**：
- 不传文件完整内容，仅传文件路径和大小
- 传文件内容前必须逐文件确认：`Send contents of config.json? (y/N)`
- 支持 `ACORN_AI_ENDPOINT` 环境变量指向私有 LLM 部署
- 无 API key 时自动降级为纯规则分析，零配置也能用

**调用时机**：仅当现有检测器置信度低于 60% 时，才建议用户启用 AI 分析。

**成本控制**：
- 每次分析最多传 20 个文件（防止 monorepo 场景 token 爆炸）
- 可配置 `ACORN_AI_MAX_FILES` 环境变量
- dry-run 模式显示将要发送的内容：`acorn analyze --dry-run --allow-ai`

**估算**：5 天（含安全审查 + 测试）。

### 3.2 模板组合系统

**替代方案**：不做预定义 `--stack`，改为"模板依赖 + overlay"机制。

```yaml
# templates/nextjs-base/template.yaml
name: nextjs-base
type: node
provides:
  - nextjs-runtime
  - react

---
# templates/tailwind-css/template.yaml
name: tailwind-css
type: node
requires:
  - react
provides:
  - tailwind
files:
  - tailwind.config.js
  - postcss.config.js

---
# templates/shadcn-ui/template.yaml  
name: shadcn-ui
type: node
requires:
  - tailwind
  - react
provides:
  - shadcn
```

```bash
acorn --with nextjs-base,tailwind-css,shadcn-ui
```

**依赖解析**：安装时自动 resolve 依赖，合并文件列表和变量。冲突时报告给用户。

**优点**：每个模板独立维护，版本兼容性在 YAML 里声明，不产生组合爆炸。

**估算**：7 天。值不值得取决于用户反馈，建议 P0/P1 做完后验证需求。

---

## 阶段四：体验打磨（P3）

详见原 DESIGN.md 的 5.1-5.3，但优先级最低。在 P0/P1 收集用户反馈前不做。

---

## 全局考量

### 后向兼容性

| 改动 | 兼容性方案 |
|------|-----------|
| 新增 `.cursorrules` | 已有文件不覆盖，除非 `--force` |
| Wizard 保存检查点 | `~/.acorn/wizard-checkpoint.json`，不影响现有配置 |
| 二进制打包 | 不改变 CLI 接口，所有 flag 兼容 |
| 模板组合系统 | 新模板用新字段，旧模板不加 `provides/requires` 也能正常使用 |

### 退出策略

每个新增命令都有对应的清理逻辑：

```bash
acorn clean                  # 清理所有 Acorn 生成的文件（交互式确认每个文件）
acorn clean --all            # 清理 + 删除模板 + 配置
acorn clean --keep-templates # 只删生成的文件，保留模板
```

实现方式：每次生成文件时记录清单到 `~/.acorn/manifest.json`：

```json
{
  "project": "/path/to/project",
  "generated_at": "2026-05-15T...",
  "files": ["Dockerfile", "docker-compose.yml", ...],
  "template": "node-api"
}
```

### 国际化维护

- Wizard 话术统一放在 `locales/zh.yaml`
- 新增字段都必须有英文 + 中文
- 缺少翻译时 silent fallback 到英文
- 不承诺多语言，只做 en/zh

### 隐私与遥测

- **默认关闭**，需要用户主动 opt-in
- 仅收集：命中的模板名称、项目类型、生成文件数
- 不收集：文件内容、项目名称、路径
- 首次运行提示：`Help improve Acorn? Share anonymous usage data (y/N)`
- 任何时候可用 `acorn telemetry disable` 关闭

### 风险登记表

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| PyInstaller 打包失败 | 中 | 高 | 0.1 阶段先验证，不行则用 Nix 或 Docker 分发 |
| macOS notarization 被拒 | 低 | 中 | 首次发布不做，标记为已知限制 |
| AI 分析数据泄露 | 低 | 高 | 文件内容逐文件确认，支持私有部署 |
| 模板组合系统需求不足 | 中 | 低 | 先收集反馈再投入开发 |
| Homebrew tap 维护负担 | 低 | 低 | 发布流程自动化，每次 GitHub Release 自动更新 formula |

---

## 修订后路线图

```
P0 (Week 1-2)               P1 (Week 3-4)             P2  (Week 5-8)
────────────────────────    ────────────────────       ────────────────────
PyInstaller 验证 (1d)        .cursorrules 生成 (2d)     AI analyze (5d)
路径引用统一 (0.5d)          acorn dockerize (1d)       模板组合系统 (7d)
测试基础设施 (1d)            acorn add-ci GA (1d)
Homebrew tap + 构建 (3d)     ────────────────────       P3  (Future)
wizard + 错误恢复 (3d)       收集用户反馈                 体验打磨
无参数自动 wizard (0.5d)     决定 P2 优先级               社区生态

总工时: 9 天                  总工时: 4 天
```

P0 和 P1 共约 13 天（单人），之后根据用户反馈决定是否投入 P2。

---

## 附录：与现有功能的对比

| 新增命令 | 现有替代 | 差异 |
|---------|---------|------|
| `acorn wizard` | `acorn --interactive` | wizard 是引导式多步骤，interactive 是精简选择 |
| `acorn dockerize` | `acorn --dir . --force` | dockerize 只生成 Docker 相关文件，不改动其他 |
| `acorn add-ci` | 无 | 全新功能 |
| `acorn analyze` | `acorn --dir .` | 现有的是规则检测，analyze 是 AI 增强 |
| `acorn clean` | 无 | 全新功能 |
