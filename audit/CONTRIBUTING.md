# Contributing to OSS Audit

Thank you for your interest in contributing to OSS Audit! This document provides guidelines for contributing to the project.

## How to Contribute

### 1. Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/oss-audit.git
   cd oss-audit
   ```

### 2. Set Up Development Environment

1. Install dependencies:
   ```bash
   pip install -e .[dev]
   ```

2. Install development dependencies:
   ```bash
   pip install pytest pylint black
   ```

### 3. Make Changes

1. Create a new branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the coding standards below

3. Test your changes:
   ```bash
   # Run tests
   pytest tests/

   # Run linting
   pylint src/

   # Test the audit tool
   python main.py /path/to/test/project
   ```

### 4. Submit a Pull Request

1. Commit your changes with a clear commit message
2. Push to your fork
3. Create a Pull Request with a clear description

## Coding Standards

### Python Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for all functions and classes
- Keep functions small and focused

### Commit Messages

Use conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Examples:
- `feat(audit): add new security dimension`
- `fix(reports): correct HTML report generation`
- `docs(readme): update installation instructions`

## Development Guidelines

### Adding New Audit Dimensions

1. Create or extend logic in `src/oss_audit/core/audit_runner.py` following the existing patterns:
   ```python
   def test_dimension_X(project_path, reports_dir, project_name):
       """测试维度X：维度名称"""
       # Implementation
   ```

2. Wire the new logic into the orchestration flow (see `AuditRunner` and `main()`).

3. Update the dimension names list in `generate_overview()`

4. Add tests in `tests/`

### Testing

- Write unit tests for new features
- Ensure all tests pass before submitting PR
- Test with different project types

## Questions or Problems?

If you have questions or encounter problems, please:

1. Check existing issues on GitHub
2. Create a new issue with a clear description
3. Join our discussions

Thank you for contributing to OSS Audit!
