# Contributing / 贡献指南

## Development Setup / 开发环境搭建

```bash
git clone https://github.com/SilasFu/Acorn.git
cd acorn
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,network,advanced]"
```

## Running Tests / 运行测试

```bash
pytest tests/ --cov=src/acorn
```

## Linting / 代码检查

```bash
ruff check src/ tests/
```

## Code Style / 代码规范

- Follow existing patterns. / 遵循现有代码风格。
- Maintain 100% test coverage. / 保持 100% 测试覆盖率。
- Keep hard dependencies minimal (only pyyaml). / 保持核心依赖最小（仅 pyyaml）。
