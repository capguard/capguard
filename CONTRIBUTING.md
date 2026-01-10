# Contributing to CapGuard

First off, **thank you** for considering contributing to CapGuard! 🎉

CapGuard is an open-source security library designed to protect LLM agents from prompt injection attacks. We welcome contributions from the community - whether it's bug reports, feature requests, documentation improvements, or code contributions.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)

---

## Code of Conduct

This project adheres to a simple code of conduct:

- **Be respectful** - Treat everyone with respect and kindness
- **Be collaborative** - Work together constructively
- **Be professional** - Keep discussions focused on technical merit
- **Be security-conscious** - This is a security library; security comes first

## How Can I Contribute?

### 🐛 Reporting Bugs

Found a bug? Please open an issue with:

- **Clear title** - Describe the bug in one sentence
- **Steps to reproduce** - How can we reproduce the issue?
- **Expected behavior** - What should happen?
- **Actual behavior** - What actually happens?
- **Environment** - Python version, OS, etc.

### 💡 Suggesting Features

Have an idea? We'd love to hear it! Open an issue with:

- **Use case** - What problem does this solve?
- **Proposed solution** - How would you implement it?
- **Alternatives considered** - What else did you think about?

### 📝 Improving Documentation

Documentation is crucial for adoption. Contributions welcome:

- Fix typos or clarify existing docs
- Add examples or use cases
- Improve README or API documentation
- Write tutorials or blog posts

### 🔧 Contributing Code

Ready to code? Awesome! See [Development Setup](#development-setup) below.

---

## Development Setup

### Prerequisites

- **Python 3.9+** (we support 3.9-3.12)
- **Git**
- **pip** (or your preferred package manager)

### Setup Steps

1. **Fork the repository**

   Click "Fork" on GitHub, then clone your fork:

   ```bash
   git clone https://github.com/YOUR_USERNAME/capguard.git
   cd capguard
   ```

2. **Create a virtual environment** (recommended)

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install CapGuard in development mode**

   ```bash
   pip install -e ".[dev]"
   ```

   This installs:
   - Core dependencies (`pydantic`)
   - Dev tools (`pytest`, `black`, `ruff`, `mypy`)

4. **Verify installation**

   ```bash
   python examples/basic_demo.py
   ```

   You should see the demo run successfully with an attack being blocked!

5. **Run tests**

   ```bash
   pytest
   ```

---

## Pull Request Process

### Branch Strategy

We follow **Gitflow**:

- `main` - Production-ready code (stable releases)
- `dev` - Integration branch (active development)
- `feat/your-feature` - Feature branches (create from `dev`)
- `fix/bug-name` - Bug fix branches (create from `dev`)
- `hotfix/critical-bug` - Hotfixes (create from `main`)

### Creating a Pull Request

1. **Create a feature branch from `dev`**

   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes**

   - Write clean, readable code
   - Add tests for new functionality
   - Update documentation if needed

3. **Commit with Conventional Commits**

   We use [Conventional Commits](https://www.conventionalcommits.org/):

   ```bash
   git commit -m "feat: add embedding-based classifier"
   git commit -m "fix: resolve constraint validation bug"
   git commit -m "docs: update installation instructions"
   ```

   **Prefixes**:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation
   - `style:` - Code formatting (no logic change)
   - `refactor:` - Code restructuring (no behavior change)
   - `test:` - Add or update tests
   - `chore:` - Maintenance tasks

4. **Run quality checks**

   ```bash
   # Format code
   black .
   
   # Lint
   ruff check .
   
   # Type check
   mypy src/capguard
   
   # Test
   pytest
   ```

5. **Push and create PR**

   ```bash
   git push origin feat/your-feature-name
   ```

   Open a PR on GitHub targeting the `dev` branch.

6. **PR Requirements**

   Your PR must:
   - ✅ Pass all CI checks
   - ✅ Include tests (80%+ coverage)
   - ✅ Follow coding standards
   - ✅ Update docs if needed
   - ✅ Have a clear description

---

## Coding Standards

### Code Style

We use **Black** for formatting and **Ruff** for linting:

```bash
black .           # Auto-format
ruff check .      # Lint
```

### Type Hints

**Type hints are required** for all public APIs:

```python
def create_token(
    user_request: str,
    granted_tools: dict[str, bool],
    confidence: float = 1.0
) -> CapabilityToken:
    """Create a capability token."""
    ...
```

Run type checking with:

```bash
mypy src/capguard
```

### Docstrings

Use **Google-style docstrings** for all public functions/classes:

```python
def classify(self, user_request: str) -> CapabilityToken:
    """Classify user intent and return capability token.
    
    Args:
        user_request: The user's natural language request
        
    Returns:
        CapabilityToken with granted tools and confidence
        
    Raises:
        ValueError: If user_request is empty
    """
    ...
```

### Error Handling

- Use custom exceptions from `capguard.core.exceptions`
- Wrap external operations in try/except
- Provide meaningful error messages

---

## Testing Guidelines

### Writing Tests

We use **pytest**. Tests live in `tests/`:

```
tests/
├── core/
│   ├── test_models.py
│   ├── test_registry.py
│   ├── test_classifier.py
│   └── test_enforcer.py
└── classifiers/
    └── test_rule_based.py
```

### Test Structure

```python
import pytest
from capguard import ToolRegistry, create_tool_definition

def test_register_tool():
    """Test tool registration."""
    registry = ToolRegistry()
    tool_def = create_tool_definition(
        name="test_tool",
        description="Test",
        risk_level=1
    )
    
    registry.register(tool_def, lambda: None)
    
    assert registry.get_tool("test_tool") is not None
```

### Coverage

- **Minimum 80% coverage** for new code
- Run coverage report:

  ```bash
  pytest --cov=capguard --cov-report=html
  ```

---

## Security Contributions

**Found a security vulnerability?** 

⚠️ **DO NOT open a public issue!**

Email us at: **security@capguard.com** (or the maintainer directly)

We'll work with you to:
1. Confirm the vulnerability
2. Develop a fix
3. Release a patch
4. Credit you (if desired)

---

## Questions?

- **General questions**: Open a GitHub Discussion
- **Bug reports**: Open an issue
- **Security concerns**: Email security@capguard.com
- **Feature ideas**: Open an issue with the "enhancement" label

---

## Recognition

Contributors will be:
- Listed in `CONTRIBUTORS.md`
- Credited in release notes
- Mentioned in blog posts (for major contributions)

---

**Thank you for making CapGuard better! 🚀**

---

*This project is licensed under Apache 2.0. By contributing, you agree to license your contributions under the same license.*
