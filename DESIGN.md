# acorn 设计文档

## 1. 概述

一个灵活的智能项目初始化工具，自动检测项目类型、匹配模板、生成配置。

## 2. 核心功能

### 2.1 智能检测
- 扫描当前目录文件结构
- 识别语言/框架类型
- 检测已有配置文件，决定增量更新或全新生成

### 2.2 模板引擎
- 模板库：预置 + 自定义 + 社区
- 变量替换：`{{name}}`, `{{port|3000}}` 等
- 模板继承：基础配置 + 项目类型扩展

### 2.3 自动生成
- 无匹配模板时，根据项目结构自动分析生成
- 生成 Dockerfile, docker-compose.yml 等

### 2.4 交互式扩展
- 不匹配时提示用户选择
- 用户确认后可保存为新模板

## 3. 系统架构

```
┌─────────────────────────────────────────┐
│     init-project (CLI 入口)     │
└─────────────────┬───────────────────────┘
         │
    ┌─────────▼──────────┐
    │  Detector    │ ← 智能检测项目类型
    └─────────┬──────────┘
         │
    ┌─────────▼──────────┐
    │  TemplateEngine │ ← 模板匹配 + 渲染
    └──┬──────────┬───────┘
      │     │
    已有模板  自动生成
```

## 4. 目录结构

```
~/.config/acorn/       # 全局配置（XDG 标准）
├── config.yaml
├── locales/
│  ├── en.yaml
│  └── zh.yaml
├── templates/           # 用户自定义模板
├── detectors/           # 用户自定义检测规则
├── plugins/            # 插件目录
│  ├── my_detector.py
│  └── my_generator.py
├── commands/            # 自定义命令
│  ├── deploy.py
│  └── migrate.py
├── cache/
└── logs/
  └── acorn.log

~/.local/share/acorn/    # 模板库（可同步）
├── node-api/
├── python-fastapi/
├── react-vite/
└── golang-gin/

project/
├── .acorn/         # 项目级配置
│  └── metadata.yaml       # 记录使用的模板版本
└── (生成的文件)
```

## 5. 检测规则 DSL

### 5.1 规则格式

```yaml
# detectors/node.yaml
type: node
priority: 10

conditions:
 files:
  - package.json
 content:
  - "engines"
  - "scripts"
 dependencies:
  - express
 patterns:
  - "src/**/*.js"

indicators:
 - name: express
  check: dependencies.express
 - name: fastify
  check: dependencies.fastify
 - name: nest
  check: dependencies.@nestjs/core
 - name: next
  check: dependencies.next
```

### 5.2 DSL 语法

```
基础表达式：
 dependencies.express     # 依赖存在
 scripts.dev          # scripts 字段存在
 files.src/*.js         # 文件模式匹配
 content.*TODO.*        # 内容正则

条件表达式：
 dependencies.express AND scripts.dev
 dependencies.express OR dependencies.koa

版本条件：
 engines.node >= "18"

扩展点：
 ext:my_check_func       # 引用自定义函数
```

### 5.3 插件扩展

```python
# plugins/my_detector.py
def my_check_func(context):
  """自定义检测函数"""
  return context.project_type == "custom"
```

## 6. 模板格式

### 6.1 模板目录结构

```
templates/node-api/
├── template.yaml   # 模板元信息
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── files/
  └── .nvmrc
```

### 6.2 template.yaml 格式

```yaml
name: node-api
description: Node.js API 项目模板
version: 1.0.0
author: your-name
homepage: https://github.com/user/node-api
tags: [node, api, express]
min_tool_version: "0.1.0"

project_type: node

detectors:
 files:
  - package.json
 keywords:
  - express
  - koa
  - fastify

variables:
 - name: port
  default: "3000"
  prompt: "应用端口"
 - name: node_version
  default: "20"
 - name: package_manager
  default: "npm"
  options: [npm, yarn, pnpm]

extends: base

files:
 - Dockerfile
 - docker-compose.yml
 - .env.example

hooks:
 before_generate: echo "Starting..."
 after_generate: echo "Done!"
```

## 7. 变量系统

### 7.1 语法

```
基础替换：
 {{name}}         → 简单替换
 {{port|3000}}      → 带默认值
 {{date}}         → 内置变量（创建日期）
 {{time}}         → 内置变量（创建时间）
 {{user}}          → 内置变量（用户名）

条件渲染：
 {{#if has_docker}}
 Dockerfile 内容...
 {{/if}}

循环渲染：
 {{#each services}}
 - {{name}}: {{port}}
 {{/each}}

变量来源（优先级）：
 CLI 参数 -v key=value > 交互输入 > 模板默认值 > 自动探测
```

### 7.2 内置变量

| 变量 | 说明 |
|------|------|
| `{{date}}` | 创建日期（YYYY-MM-DD） |
| `{{time}}` | 创建时间（HH:MM:SS） |
| `{{user}}` | 当前用户名 |
| `{{cwd}}` | 当前工作目录 |
| `{{project_name}}` | 从目录名提取 |

## 8. 模板继承

### 8.1 继承规则

```
1. 单层继承：base → 具体模板（不允许多层）
2. 文件覆盖：子模板同名文件替换父模板
3. 变量合并：子模板变量追加到父模板，重复 name 则 override
4. 目录合并：子模板目录下的文件追加到父模板
```

### 8.2 示例

```
base/
├── Dockerfile
├── docker-compose.yml
└── template.yaml

node-api/
├── Dockerfile       # 覆盖 base
├── .nvmrc         # 新增
└── template.yaml     # extends: base

生成结果：
 Dockerfile (node-api 的)
 docker-compose.yml (base 的)
 .nvmrc (node-api 的)
```

## 9. 自动生成

### 9.1 分析阶段

```
1. 扫描项目结构（目录树、文件类型）
2. 读取依赖文件（package.json, requirements.txt 等）
3. 检测入口文件和端口（listen(), app.run 等）
4. 推断项目类型和框架
```

### 9.2 生成阶段

```
1. 根据依赖动态生成 Dockerfile（检测到 prisma → 安装 prisma）
2. 根据入口文件推断启动命令
3. 根据端口代码推断默认端口
```

### 9.3 更新策略

```
1. 已有配置 → 询问用户：覆盖/保留/增量更新
2. 备份原文件（.bak 后缀）
3. 标记生成的配置文件（添加注释）
4. 支持 --regenerate 重新生成
```

### 9.4 空项目处理

```
空目录检测流程：
1. 检测到目录为空/极少文件
2. 立即进入引导模式
3. 收集基本信息后再生成
```

## 10. 交互流程

### 10.1 流程设计

```
1. 先自动检测（如果已有项目）
2. 检测到 → 确认而非重选
3. 检测不到 → 进入引导

用户确认模式：
┌─────────────────────────────┐
│ 🔍 检测到: Node.js 项目   │
│  框架: Express       │
│               │
│ [Y] 确认使用此类型     │
│ [N] 手动选择        │
│ [Q] 退出          │
└─────────────────────────────┘

变量填写：
┌─────────────────────────────┐
│ 📝 配置项目变量       │
│               │
│ 项目名称: my-project [✓]  │
│ 端口: 3000 [✓]       │
│ Node版本: 18 [✓]      │
│               │
│ [E] 编辑 [C] 继续 [Q] 退出│
└─────────────────────────────┘
```

### 10.2 交互规范

```
- 彩色输出 + 序号选择
- 回车确认默认值
- Ctrl+C 优雅退出
- 已填信息可回退修改
- 支持 --lang zh 切换中文
```

## 11. 边界情况处理

### 11.1 混合项目

```
检测到多种项目类型：
┌─────────────────────────────┐
│ 🔍 检测到多种项目类型:    │
│  [1] Node.js (package.json)│
│  [2] Python (requirements) │
│  [3] 生成双配置      │
│  [0] 取消         │
└─────────────────────────────┘
```

### 11.2 文件冲突

```
已有配置文件冲突：
┌─────────────────────────────┐
│ ⚠️ Dockerfile 已存在    │
│ [B] 备份后覆盖 (.bak)    │
│ [K] 保留现有        │
│ [D] 显示差异        │
│ [Q] 取消          │
└─────────────────────────────┘
```

### 11.3 其他边界

| 场景 | 处理方式 |
|------|----------|
| 权限问题 | 友好提示 + 建议 |
| 网络失败 | 静默跳过（--verbose 显示） |
| 空目录 | 引导选择模板 |
| 单文件项目 | 检测语言，生成最小配置 |

## 12. 版本管理

### 12.1 模板版本

```
- 模板带版本号，支持多版本共存
- 内置模板：用户可 fork 后自定义
- 升级提示：
┌─────────────────────────────┐
│ ⚠️ 模板有新版本 v1.2.0   │
│ 当前: v1.1.0        │
│               │
│ [U] 升级          │
│ [K] 保持当前        │
│ [D] 查看差异        │
└─────────────────────────────┘
```

### 12.2 工具版本

```
- acorn version 显示当前版本
- acorn check-update 检查更新
- 配置文件有版本标记（config_version: "1.0"）
- 升级时自动迁移配置（向前兼容）
```

## 13. CLI 命令设计

### 13.1 常用选项（扁平）

```
acorn help
acorn version
acorn check-update
acorn list
acorn add <path>
acorn remove <name>
acorn search <keyword>
acorn install <template>
acorn update
acorn export
acorn import <file>
acorn init
```

### 13.2 扩展命令（嵌套）

```
acorn template list
acorn template add <path>
acorn template remove <name>
acorn template install <user/repo>

acorn plugin list
acorn plugin add <path>

acorn config init
acorn config export
acorn config import

acorn deploy
acorn migrate
```

### 13.3 全局选项

```
--help, -h      # 显示帮助
--version, -v    # 显示版本
--verbose      # 详细输出
--debug       # 调试模式
--quiet       # 静默模式
--config <path>   # 指定配置文件
--lang <lang>    # 语言 (en/zh)
--offline      # 离线模式
```

## 14. 日志系统

### 14.1 日志级别

```
ERROR  → 红色，错误信息
WARNING → 黄色，警告（可忽略但建议处理）
INFO  → 白色，重要信息（默认显示）
DEBUG  → 灰色，详细信息（--verbose 显示）
```

### 14.2 输出格式

```
┌─────────────────────────────────┐
│ ERROR: 模板未找到        │
│ → 运行 acorn list 查看 │
│ → 或使用 --template 指定    │
└─────────────────────────────────┘
```

### 14.3 日志文件

```
~/.local/share/acorn/logs/acorn.log
自动轮转（保留 7 天）
```

## 15. 安全

### 15.1 模板安全

```
- 安装时验证 template.yaml 格式
- 扫描 Dockerfile 危险指令（如 RUN curl | sh）

检测到可疑指令时：
┌─────────────────────────────────┐
│ ⚠️ 检测到可疑指令       │
│ 文件: Dockerfile        │
│ 内容: RUN curl | sh      │
│ [I] 忽略并继续         │
│ [V] 查看详情          │
│ [A] 中止安装         │
└─────────────────────────────────┘
```

### 15.2 敏感信息

```
- 生成 .env.example 时提示检查 .gitignore
- 检测可能泄露的示例值（fake key 等）
```

### 15.3 网络安全

```
- --offline 模式跳过所有网络操作
- 超时 10s，失败后提示
- 不记录敏感请求头
```

### 15.4 文件权限

```
- 配置文件：644
- 脚本文件：755
- 目录：755
```

## 16. 国际化

### 16.1 支持语言

```
- 英语 (en) - 默认
- 中文 (zh)
```

### 16.2 切换方式（优先级）

```
1. CLI 参数：--lang zh
2. 环境变量：ACORN_LANG=zh
3. 配置文件：default_lang: zh
4. 系统语言：LANG 环境变量
```

### 16.3 翻译文件格式

```yaml
# locales/zh.yaml
messages:
 detecting: "正在检测项目类型..."
 detected: "检测到: {{type}}"
 error:
  not_found: "未找到"
  permission_denied: "权限不足"
```

## 17. 扩展机制

### 17.1 插件系统

```
~/.config/acorn/plugins/
├── my_detector.py   # 自定义检测器
└── my_generator.py  # 自定义生成器

Hook 触发点：
- before_detect()  # 检测前
- after_detect()   # 检测后
- before_generate() # 生成前
- after_generate()  # 生成后
```

### 17.2 插件示例

```python
# plugins/my_detector.py
def before_detect(context):
  """检测前执行"""
  print(f"即将检测: {context.project_path}")
  return context

def after_detect(context, result):
  """检测后执行"""
  print(f"检测结果: {result}")
  return result
```

### 17.3 自定义命令

```
~/.config/acorn/commands/
├── deploy.py    # acorn deploy
└── migrate.py    # acorn migrate
```

## 18. 模板市场

### 18.1 架构

```
- 官方模板：内置
- 社区模板：托管在 GitHub
- 格式：模板仓库根目录有 template.yaml
```

### 18.2 命令

```
acorn search fastapi    # 搜索 GitHub
acorn install user/repo   # 安装模板

acorn update-templates   # 批量更新
acorn update <name>     # 单个更新
```

### 18.3 社区规范

```
- 仓库名以 acorn- 开头
- 或有 .acorn 主题标签
- template.yaml 包含完整元数据
```

## 19. 依赖

### 19.1 核心依赖

```toml
dependencies = [
  "pyyaml>=6.0",
]
```

### 19.2 可选依赖

```toml
extras = {
  "color": ["colorama"],
  "network": ["requests"],
  "advanced": ["jinja2"],
}
```

## 20. 测试

### 20.1 测试结构

```
tests/
├── unit/          # 单元测试
│  ├── test_detector.py
│  ├── test_template.py
│  └── test_variables.py
├── integration/       # 集成测试
│  ├── test_cli.py
│  └── test_project_flow.py
└── fixtures/        # 测试数据
  ├── node-project/
  └── python-project/
```

### 20.2 CI/CD

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
 test:
  runs-on: ubuntu-latest
  strategy:
   matrix:
    python-version: ["3.10", "3.11", "3.12"]
  steps:
   - uses: actions/checkout@v4
   - name: Set up Python ${{ matrix.python-version }}
    uses: actions/setup-python@v5
    with:
     python-version: ${{ matrix.python-version }}
   - name: Install dependencies
    run: pip install -e ".[dev]"
   - name: Lint
    run: ruff check .
   - name: Type check
    run: mypy src/
   - name: Test
    run: pytest --cov=src tests/
```

## 21. 技术选型

| 组件 | 选择 |
|------|------|
| 语言 | Python 3.10+ |
| 构建 | hatchling |
| CLI | argparse（标准库） |
| 配置 | YAML |
| 测试 | pytest |
| 代码质量 | ruff, mypy |

## 22. 开发计划

### Phase 1: 核心功能
- [ ] 检测引擎（DSL + 评分制）
- [ ] 模板引擎（继承 + 变量 + 条件）
- [ ] 自动生成
- [ ] 交互式流程

### Phase 2: 扩展功能
- [ ] 插件系统
- [ ] 自定义命令
- [ ] 模板市场
- [ ] 国际化

### Phase 3: 完善
- [ ] 测试覆盖 > 80%
- [ ] CI/CD
- [ ] 文档
- [ ] 发布 PyPI