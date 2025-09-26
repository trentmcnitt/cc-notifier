# Fix Command

Runs comprehensive quality checks and fixes any issues found.

## Usage
```
/fix
```

## What it does
1. Runs `source .venv/bin/activate && make check` to perform code quality checks.
2. If any issues are found, it attempts to fix them automatically (e.g., formatting code, reformatting, etc.).
3. Runs `make check` again to ensure all issues are resolved.
4. Repeats the process until no issues remain, or a maximum number of attempts is reached (to avoid infinite loops).

## Command
```bash
make check
```