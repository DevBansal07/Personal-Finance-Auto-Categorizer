# Contributing to SpendSense

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to SpendSense.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:

- A clear, descriptive title.
- Steps to reproduce the behavior.
- Expected behavior vs. actual behavior.
- Your Python version (`python --version`).
- A sample of the bank statement format (anonymized) that caused the issue, if applicable.

### Suggesting Features

Feature requests are welcome! Please open an issue describing:

- The problem your feature would solve.
- Your proposed solution.
- Any alternatives you've considered.

### Adding Category Keywords

The easiest way to contribute is by expanding the keyword mappings in `config/categories.json`:

1. Fork the repository.
2. Add keywords to existing categories or create new ones.
3. Test with a sample statement to verify the new keywords match correctly.
4. Submit a pull request.

### Code Contributions

1. **Fork** the repository and create your branch from `main`.
2. **Set up** your development environment:

   ```bash
   git clone https://github.com/yourusername/spendsense.git
   cd spendsense
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Make your changes** following the code style guidelines below.
4. **Test** your changes against the sample data:

   ```bash
   python main.py --file sample_data/sample_statement.csv
   ```

5. **Submit** a pull request with a clear description of the changes.

## Code Style Guidelines

- **Python 3.11+** — Use modern type hints (`list[str]`, `dict[str, str]`, `X | None`).
- **Docstrings** — Google-style docstrings for all public functions and classes.
- **Logging** — Use the `spendsense.logger.get_logger()` factory; never use `print()` for status messages.
- **Exceptions** — Raise custom exceptions from `spendsense.exceptions` instead of generic `ValueError`/`RuntimeError`.
- **Imports** — Standard library first, then third-party, then local. Alphabetical within each group.
- **Naming** — `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.

## Project Structure

| Module | Responsibility |
|--------|---------------|
| `spendsense/data_loader.py` | File I/O, column validation, type coercion |
| `spendsense/categorizer.py` | Description cleaning, keyword matching |
| `spendsense/reporter.py` | Analytics computation, HTML report generation |
| `spendsense/exceptions.py` | Custom exception hierarchy |
| `spendsense/logger.py` | Logging configuration |
| `main.py` | CLI parsing, pipeline orchestration |

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
