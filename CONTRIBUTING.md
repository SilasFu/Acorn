# Contributing

## Development Setup

```bash
git clone https://github.com/SilasFu/Acorn.git
cd acorn
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,network,advanced]"
```

## Running Tests

```bash
pytest tests/ --cov=src/acorn
```

## Linting

```bash
ruff check src/ tests/
```

## Code Style

- Follow existing patterns.
- Maintain 100% test coverage.
- Keep hard dependencies minimal (only pyyaml).
