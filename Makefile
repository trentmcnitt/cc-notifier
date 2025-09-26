# Claude Code Notifier - Development Commands

.PHONY: help install format lint lint-fix typecheck test deadcode shell-lint check clean

help: ## Show this help
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# QUALITY CHECK PATTERN
# ============================================================================

# Standard pattern: try quiet, show verbose on failure
define quality_check
	@$(1) >/dev/null 2>&1 && echo "✅ $(2): PASSED" || (echo "❌ $(2): FAILED" && $(1) && false)
endef

# ============================================================================
# DEVELOPMENT
# ============================================================================

install: ## Install development dependencies
	pip3 install -e ".[dev]"

format: ## Format code with ruff
	$(call quality_check,ruff format *.py tests/,FORMAT)

lint: ## Lint with ruff (comprehensive check)
	$(call quality_check,ruff check *.py tests/,LINT)

lint-fix: ## Auto-fix linting issues with ruff
	$(call quality_check,ruff check *.py tests/ --fix,LINT-FIX)

typecheck: ## Type check with mypy
	$(call quality_check,mypy *.py,TYPECHECK)

test: ## Run tests
	@pytest -s && echo "✅ TEST: PASSED" || (echo "❌ TEST: FAILED" && false)

deadcode: ## Find dead/unused code with vulture
	$(call quality_check,vulture *.py tests/ --min-confidence 70,DEADCODE)

shell-lint: ## Lint shell scripts (preserved from original)
	@echo "🐚 Linting shell scripts..."
	@shellcheck --severity=info --enable=all *.sh && echo "✅ Shell lint: PASSED" || (echo "❌ Shell lint: FAILED" && false)

check: ## Run comprehensive quality checks
	@echo "🔍 Running comprehensive quality checks..."
	@$(MAKE) -k format lint typecheck test deadcode shell-lint && echo "\n🎉 CHECK PASSED" || echo "\n❌ CHECK FAILED"

clean: ## Clean up temporary files
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".ruff_cache" -delete
	find . -type d -name ".mypy_cache" -delete
	find . -name "*.log" -delete
	find . -name "*~" -delete
	find . -name "*.tmp" -delete
	@echo "✅ Cleaned temporary files"