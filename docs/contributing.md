# Contributing to Django Testimonials

Thank you for your interest in contributing to Django Testimonials! This guide will help you get started with contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)
- [Documentation](#documentation)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## Getting Started

### Prerequisites

- Python 3.8+
- Git
- Basic knowledge of Django and Django REST Framework

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/NzeStan/django-testimonials.git
   cd django-testimonials
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/NzeStan/django-testimonials.git
   ```

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install development dependencies:
   ```bash
   pip install -e .[dev]
   ```

3. Set up the test database:
   ```bash
   python -m pytest --create-db
   ```

## Making Changes

### Branch Strategy

1. Create a new branch for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

2. Keep your branch up to date:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

### Development Guidelines

- Follow Django best practices
- Write meaningful commit messages
- Keep changes focused and atomic
- Update documentation when necessary
- Add tests for new functionality

## Testing

### Running Tests

Run the full test suite:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=testimonials --cov-report=html
```

Run specific tests:
```bash
pytest tests/test_models.py
pytest tests/test_api.py::TestTestimonialAPI::test_create_testimonial
```

### Test Requirements

- All new features must include tests
- Bug fixes should include regression tests
- Aim for high test coverage (>90%)
- Tests should be fast and reliable

### Test Structure

```
tests/
├── __init__.py
├── settings.py          # Test Django settings
├── test_models.py       # Model tests
├── test_api.py         # API endpoint tests
├── test_admin.py       # Admin interface tests
├── test_signals.py     # Signal tests
└── factories.py        # Factory Boy factories
```

## Code Style

This project uses several tools to maintain code quality:

### Formatting and Linting

- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting
- **Ruff**: Fast Python linter

Run formatting:
```bash
black .
isort .
```

Run linting:
```bash
ruff check .
```

### Code Standards

- Follow PEP 8
- Use descriptive variable and function names
- Add docstrings to public methods and classes
- Use type hints where appropriate
- Keep functions small and focused

### Example Code Style

```python
from typing import Optional
from django.db import models
from django.utils.translation import gettext_lazy as _


class Testimonial(models.Model):
    """A customer testimonial with rating and approval status."""
    
    author_name: str = models.CharField(
        _("Author Name"),
        max_length=100,
        help_text=_("Name of the person giving the testimonial")
    )
    
    def __str__(self) -> str:
        return f"Testimonial by {self.author_name}"
    
    def get_absolute_url(self) -> str:
        """Return the canonical URL for this testimonial."""
        return reverse("testimonials:detail", kwargs={"pk": self.pk})
```

## Submitting Changes

### Pull Request Process

1. Ensure all tests pass:
   ```bash
   pytest
   ```

2. Update documentation if needed

3. Push your branch:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a Pull Request on GitHub with:
   - Clear title and description
   - Reference to related issues
   - Screenshots for UI changes
   - Testing notes

### Pull Request Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated (if applicable)
- [ ] No breaking changes (or clearly documented)
- [ ] Commit messages are clear and descriptive

## Reporting Issues

### Bug Reports

When reporting bugs, please include:

- Django version
- Python version
- Package version
- Steps to reproduce
- Expected vs actual behavior
- Error messages/stack traces
- Minimal code example

### Feature Requests

For feature requests, please describe:

- The problem you're trying to solve
- Your proposed solution
- Alternative solutions considered
- How it would benefit other users

## Documentation

### Building Documentation Locally

1. Install documentation dependencies:
   ```bash
   pip install -e .[dev]
   ```

2. Build documentation:
   ```bash
   mkdocs serve
   ```

3. View at `http://localhost:8000`

### Documentation Guidelines

- Use clear, concise language
- Include code examples
- Update API documentation for changes
- Test all code examples
- Follow existing documentation structure

## Development Workflow Summary

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create** a feature branch
4. **Make** your changes with tests
5. **Run** tests and linting
6. **Commit** with clear messages
7. **Push** to your fork
8. **Submit** a Pull Request

## Getting Help

- Check existing [Issues](https://github.com/NzeStan/django-testimonials/issues)
- Read the [Documentation](https://django-testimonials.readthedocs.io/)
- Start a [Discussion](https://github.com/NzeStan/django-testimonials/discussions)

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes for significant contributions
- GitHub contributors page

Thank you for contributing to Django Testimonials! 🎉