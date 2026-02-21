<!-- filepath: CONTRIBUTING.md -->

# Contributing to AdManager

Thank you for your interest in contributing to AdManager! This document provides guidelines and instructions for contributing to this project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Git Flow](#git-flow)
- [Testing](#testing)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Follow the project's technical standards
- Respect the proprietary license — do not share code externally

---

## Getting Started

### Prerequisites

- **Python:** 3.11+ (managed via `uv`)
- **Docker & Docker Compose:** For running PostgreSQL and Qdrant
- **Git:** For version control
- **Pre-commit:** For code quality checks

### Fork and Clone

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/backend-for-using-ai.git
cd backend-for-using-ai

# 3. Add upstream remote
git remote add upstream https://github.com/GloryWater/backend-for-using-ai.git
```

---

## Development Environment Setup

### 1. Install uv (Python Package Manager)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Install Dependencies

```bash
# Sync dependencies (creates .venv automatically)
uv sync
```

### 3. Setup Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Verify installation
uv run pre-commit --version
```

### 4. Start Development Services

```bash
# Start PostgreSQL and Qdrant (Docker Compose)
docker-compose up -d db qdrant

# Verify services are running
docker-compose ps
```

### 5. Run Database Migrations

```bash
# Apply migrations to create tables
uv run alembic upgrade head
```

### 6. Verify Setup

```bash
# Run quick tests
uv run pytest tests/ -v

# Check code quality
uv run pre-commit run --all-files
```

---

## Git Flow

### Branch Naming Conventions

Use the following format for branch names:

```
<type>/<description>
```

**Types:**
- `feature/` — New features (e.g., `feature/add-payment-webhook`)
- `fix/` — Bug fixes (e.g., `fix/rate-limit-bug`)
- `refactor/` — Code refactoring (e.g., `refactor/ai-service-structure`)
- `docs/` — Documentation updates (e.g., `docs/update-readme`)
- `test/` — Adding or updating tests (e.g., `test/add-chaos-tests`)
- `chore/` — Maintenance tasks (e.g., `chore/update-dependencies`)

**Examples:**
```
feature/telegram-stars-payment
fix/hwid-reset-in-bot
refactor/database-connection-pool
docs/add-api-examples
test/load-testing-suite
chore/bump-fastapi-version
```

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `style:` — Code style changes (formatting, semicolons, etc.)
- `refactor:` — Code refactoring
- `test:` — Adding tests
- `chore:` — Maintenance tasks

**Examples:**
```
feat(payments): add Tribute webhook support

Implemented HMAC-SHA256 signature verification for Tribute webhooks.
Added idempotency checks to prevent duplicate payment processing.

Closes #42

---

fix(auth): resolve HWID binding issue on license activation

The HWID was not being saved correctly when activating a new license.
This caused users to be unable to use their license on the first device.

Fixes #38
```

### Workflow

```bash
# 1. Create a new branch from main
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name

# 2. Make changes and commit
git add .
git commit -m "feat(scope): add new feature"

# 3. Push to your fork
git push origin feature/your-feature-name

# 4. Create a Pull Request on GitHub
#    Go to the repository → Pull Requests → New Pull Request
```

---

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_api.py -v

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS/Linux
start htmlcov\index.html  # Windows
```

### Load Testing

```bash
# Run load tests (requires --load flag)
uv run pytest tests/load/ -v --load

# Run full load test suite (stress, soak, spike, chaos)
uv run pytest tests/load/ -v --load --full-mode

# Run specific load test
uv run pytest tests/load/test_stress.py -v --load
```

### Test Requirements

Before submitting a PR:

- ✅ **All existing tests must pass** (`uv run pytest`)
- ✅ **New features require new tests** (unit or integration)
- ✅ **Bug fixes require regression tests**
- ✅ **Load tests should be updated** if performance is affected

### Writing Tests

**Test File Structure:**
```python
# tests/test_your_feature.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_your_feature():
    """Test description here."""
    # Arrange
    test_data = {"key": "test_value"}
    
    # Act
    response = client.post("/endpoint", json=test_data)
    
    # Assert
    assert response.status_code == 200
    assert response.json()["result"] == "expected_value"
```

**Fixtures (tests/conftest.py):**
```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

@pytest.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        # Create tables
        pass
    
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
    
    # Cleanup
    await engine.dispose()
```

---

## Code Style

### Linting and Formatting

We use **Ruff** for linting and formatting:

```bash
# Check code (auto-fix where possible)
uvx ruff check . --fix

# Format code
uvx ruff format .

# Type checking with Mypy
uv run mypy src/
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`:

- ✅ **Ruff** — Linting and formatting
- ✅ **Mypy** — Type checking (excludes `alembic/` and `src/bot/`)

If pre-commit fails:

```bash
# Run pre-commit manually to see errors
uv run pre-commit run --all-files

# Fix issues and try again
git add .
git commit -m "fix: resolve pre-commit errors"
```

### Code Style Guidelines

**Imports:**
```python
# Standard library
import os
from typing import Optional

# Third-party
from fastapi import FastAPI
from pydantic import BaseModel

# First-party
from src.config import settings
from src.database.models import User
```

**Type Hints:**
```python
# ✅ Good
def calculate_price(base: float, discount: float) -> float:
    return base * (1 - discount)

# ❌ Bad
def calculate_price(base, discount):
    return base * (1 - discount)
```

**Async/Await:**
```python
# ✅ Good
async def get_user(telegram_id: int) -> User | None:
    async with db_session() as session:
        return await session.get(User, telegram_id)

# ❌ Bad (blocking call in async function)
async def get_user(telegram_id: int) -> User | None:
    return db_session.get(User, telegram_id)  # Blocks event loop!
```

**Error Handling:**
```python
# ✅ Good
try:
    result = await llm.generate(text)
except openai.APIError as e:
    logger.error("LLM API error: %s", e)
    raise HTTPException(status_code=503, detail="AI service unavailable")

# ❌ Bad
try:
    result = await llm.generate(text)
except Exception:  # Too broad!
    pass  # Silent failure
```

---

## Pull Request Process

### PR Checklist

Before submitting your PR, ensure:

- [ ] **Tests pass:** `uv run pytest`
- [ ] **Pre-commit passes:** `uv run pre-commit run --all-files`
- [ ] **Type checking passes:** `uv run mypy src/`
- [ ] **Documentation updated:** README.md, docstrings, etc.
- [ ] **Changelog updated:** (if applicable)
- [ ] **Environment variables documented:** (if adding new config)
- [ ] **No sensitive data:** API keys, passwords, etc.

### Creating a Pull Request

1. **Push your branch:**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Go to the repository on GitHub** → Pull Requests → New Pull Request

3. **Fill out the PR template:**
   - Title: Clear and descriptive
   - Description: What, why, and how
   - Link related issues (e.g., `Closes #42`)

4. **Wait for CI:**
   - GitHub Actions will run tests automatically
   - All checks must pass ✅

5. **Code Review:**
   - Maintainers will review your code
   - Address feedback and push updates
   - Be responsive to comments

### PR Title Format

```
<type>(<scope>): <description>
```

**Examples:**
```
feat(payments): add Telegram Stars support
fix(auth): resolve HWID reset issue
docs(readme): add architecture diagram
```

---

## Questions?

If you have questions or need help:

- **Check existing issues:** [GitHub Issues](https://github.com/GloryWater/backend-for-using-ai/issues)
- **Create a new issue:** Use the appropriate template
- **Contact maintainers:** Via GitHub or Telegram

---

Thank you for contributing to AdManager! 🎉
