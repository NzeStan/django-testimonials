# Contributing to Django Testimonials

Thank you for your interest in contributing! This guide will help you get started.

## Getting Started

### 1. Fork & Clone

```bash
git clone https://github.com/your-username/django-testimonials.git
cd django-testimonials
```

### 2. Set Up Development Environment

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install in development mode
pip install -e .[dev]
```

### 3. Verify Setup

```bash
python -m pytest
```

## Development Workflow

### Branch Naming

Create a branch from `main`:

```bash
git checkout -b feature/your-feature-name   # New features
git checkout -b fix/your-bug-fix             # Bug fixes
git checkout -b docs/your-doc-update         # Documentation
```

### Running Tests

```bash
# Full test suite
python -m pytest

# With coverage report
python -m pytest --cov=testimonials --cov-report=html

# Run a specific test file
python -m pytest testimonials/tests/test_model.py

# Run a specific test
python -m pytest testimonials/tests/test_model.py::TestimonialModelTests::test_create_testimonial
```

### Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for lint errors
ruff check .

# Auto-fix lint errors
ruff check --fix .

# Format code
ruff format .
```

## Making Changes

1. Write your code following existing patterns in the codebase
2. Add or update tests for your changes
3. Run the full test suite to ensure nothing is broken
4. Run the linter to check code style

## Submitting a Pull Request

1. Push your branch to your fork
2. Open a PR against `main` on the original repository
3. Fill in the PR template with:
   - A clear description of the change
   - Why the change is needed
   - How to test it
4. Ensure all CI checks pass

### PR Guidelines

- Keep PRs focused on a single change
- Write descriptive commit messages
- Update documentation if your change affects user-facing behavior
- Add tests for new functionality
- Don't break existing tests

## Reporting Bugs

Open an issue with:

- Python and Django versions
- Steps to reproduce
- Expected vs actual behavior
- Error traceback (if applicable)

## Requesting Features

Open an issue describing:

- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

## Project Structure

```
testimonials/
  models/          # Database models
  api/             # REST API (views, serializers, filters, permissions)
  dashboard/       # Admin dashboard views
  services/        # Cache and task services
  mixins/          # Reusable mixins
  tests/           # Test suite
  templates/       # HTML templates
  static/          # CSS and JS assets
```

## Code of Conduct

- Be respectful and constructive
- Focus on the code, not the person
- Welcome newcomers and help them contribute

## Questions?

- [Open an issue](https://github.com/NzeStan/django-testimonials/issues)
- [Start a discussion](https://github.com/NzeStan/django-testimonials/discussions)
