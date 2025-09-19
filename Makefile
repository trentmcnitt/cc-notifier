# Claude Code Notifier - Shell Script Quality Commands

.PHONY: help lint check clean

help: ## Show this help
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

lint: ## Lint shell scripts with shellcheck
	@shellcheck --severity=info --enable=all src/*.sh *.sh src/cc-notifier && echo "✅ LINT: PASSED" || (echo "❌ LINT: FAILED" && false)

check: ## Run quality checks
	@echo "🔍 Running shell script quality checks..."
	@$(MAKE) lint && echo "\n🎉 CHECK PASSED" || echo "\n❌ CHECK FAILED"

clean: ## Clean up temporary files
	find . -name "*.log" -delete
	find . -name "*~" -delete
	find . -name "*.tmp" -delete      
	@echo "✅ Cleaned temporary files"