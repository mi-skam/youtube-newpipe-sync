.PHONY: help prerequisites check-tools setup-github setup-gcloud get-oauth add-secrets enable-actions trigger-sync complete setup-venv test-local run-local clean-venv clean

SHELL := /bin/bash
PROJECT_NAME := tubesync
REPO_DIR := $(shell pwd)

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help:
	@echo "YouTube → NewPipe Sync Setup"
	@echo ""
	@echo "Run these targets in order:"
	@echo "  make prerequisites   - Check all required tools"
	@echo "  make setup-github    - Create GitHub repo and add all files"
	@echo "  make setup-gcloud    - Guide through Google Cloud setup"
	@echo "  make get-oauth       - Get OAuth credentials and refresh token"
	@echo "  make add-secrets     - Add secrets to GitHub"
	@echo "  make enable-actions  - Enable workflow write permissions (manual step)"
	@echo "  make trigger-sync    - Run first sync"
	@echo "  make complete        - Show final URLs and instructions"
	@echo ""
	@echo "Or run everything:"
	@echo "  make all"
	@echo ""
	@echo "Local development:"
	@echo "  make test-local      - Run tests locally (sets up venv automatically)"
	@echo "  make run-local       - Run sync locally (requires env vars)"
	@echo "  make setup-venv      - Set up Python virtual environment"
	@echo "  make clean-venv      - Remove virtual environment"

all: prerequisites setup-github setup-gcloud get-oauth add-secrets enable-actions trigger-sync complete

prerequisites:
	@echo "$(GREEN)Checking prerequisites...$(NC)"
	@command -v gh >/dev/null 2>&1 || { echo "$(RED)❌ gh CLI not found. Install: brew install gh$(NC)"; exit 1; }
	@command -v gcloud >/dev/null 2>&1 || { echo "$(RED)❌ gcloud CLI not found. Install: brew install google-cloud-sdk$(NC)"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "$(RED)❌ Python 3 not found$(NC)"; exit 1; }
	@command -v jq >/dev/null 2>&1 || { echo "$(RED)❌ jq not found. Install: brew install jq$(NC)"; exit 1; }
	@echo "$(GREEN)✅ All prerequisites installed$(NC)"
	@echo ""
	@echo "$(YELLOW)Checking authentication...$(NC)"
	@gh auth status || { echo "$(RED)Run: gh auth login$(NC)"; exit 1; }
	@gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q . || { echo "$(RED)Run: gcloud auth login$(NC)"; exit 1; }
	@echo "$(GREEN)✅ Authenticated to GitHub and Google Cloud$(NC)"

setup-github:
	@echo "$(GREEN)Setting up GitHub repository...$(NC)"
	@if gh repo view $(PROJECT_NAME) >/dev/null 2>&1; then \
		echo "$(YELLOW)Repository already exists, skipping creation$(NC)"; \
	else \
		echo "Creating repository..."; \
		gh repo create $(PROJECT_NAME) --public --description "Auto-sync YouTube subscriptions to NewPipe"; \
		echo "$(GREEN)✅ Repository created$(NC)"; \
	fi
	@echo ""
	@echo "$(GREEN)Creating project files...$(NC)"
	@$(MAKE) -s create-files
	@echo ""
	@echo "$(GREEN)Initializing git and pushing...$(NC)"
	@if [ ! -d .git ]; then git init; fi
	@git add .
	@git diff --staged --quiet || git commit -m "Initial setup for YouTube sync"
	@git branch -M main
	@git remote get-url origin >/dev/null 2>&1 || git remote add origin "git@github.com:$$(gh api user -q .login)/$(PROJECT_NAME).git"
	@git push -u origin main || echo "$(YELLOW)Already pushed$(NC)"
	@echo "$(GREEN)✅ Files pushed to GitHub$(NC)"
	@echo ""
	@echo "$(GREEN)Enabling GitHub Pages...$(NC)"
	@gh api repos/:owner/:repo/pages -f source[branch]=gh-pages -f source[path]=/ 2>/dev/null || echo "$(YELLOW)Pages already enabled or will be enabled after first workflow run$(NC)"
	@echo "$(GREEN)✅ GitHub setup complete$(NC)"

create-files:
	@echo "$(GREEN)All project files already exist$(NC)"

setup-gcloud:
	@echo "$(GREEN)Setting up Google Cloud...$(NC)"
	@echo ""
	@echo "$(YELLOW)This will guide you through Google Cloud setup$(NC)"
	@echo ""
	@read -p "Enter a project ID (e.g., youtube-sync-$$RANDOM): " PROJECT_ID; \
	echo "$$PROJECT_ID" > .gcloud-project-id; \
	echo "Creating project: $$PROJECT_ID"; \
	gcloud projects create "$$PROJECT_ID" --name="YouTube Sync" 2>/dev/null || echo "$(YELLOW)Project might already exist$(NC)"; \
	gcloud config set project "$$PROJECT_ID"; \
	echo ""; \
	echo "$(YELLOW)⚠️  You need to link a billing account.$(NC)"; \
	echo "Opening: https://console.cloud.google.com/billing/linkedaccount?project=$$PROJECT_ID"; \
	open "https://console.cloud.google.com/billing/linkedaccount?project=$$PROJECT_ID" 2>/dev/null || \
		echo "Visit: https://console.cloud.google.com/billing/linkedaccount?project=$$PROJECT_ID"; \
	read -p "Press Enter after linking billing account..."; \
	echo ""; \
	echo "Enabling YouTube Data API v3..."; \
	gcloud services enable youtube.googleapis.com; \
	echo "$(GREEN)✅ Google Cloud project configured$(NC)"

get-oauth:
	@echo "$(GREEN)Getting OAuth credentials...$(NC)"
	@echo ""
	@if [ ! -f .gcloud-project-id ]; then \
		echo "$(RED)Run 'make setup-gcloud' first$(NC)"; \
		exit 1; \
	fi
	@PROJECT_ID=$$(cat .gcloud-project-id); \
	echo "$(YELLOW)Manual steps required:$(NC)"; \
	echo ""; \
	echo "1. Configure OAuth consent screen:"; \
	echo "   https://console.cloud.google.com/apis/credentials/consent?project=$$PROJECT_ID"; \
	echo "   - User Type: External"; \
	echo "   - App name: YouTube NewPipe Sync"; \
	echo "   - Add your email as developer and test user"; \
	echo "   - Scopes: Add '../auth/youtube.readonly'"; \
	echo ""; \
	echo "2. Create OAuth Client ID:"; \
	echo "   https://console.cloud.google.com/apis/credentials?project=$$PROJECT_ID"; \
	echo "   - Create Credentials → OAuth client ID"; \
	echo "   - Application type: Desktop app"; \
	echo "   - Name: YouTube Sync"; \
	echo ""; \
	read -p "Press Enter after completing these steps..."; \
	echo ""; \
	read -p "Enter Client ID: " CLIENT_ID; \
	read -p "Enter Client Secret: " CLIENT_SECRET; \
	echo "$$CLIENT_ID" > .oauth-client-id; \
	echo "$$CLIENT_SECRET" > .oauth-client-secret; \
	echo ""; \
	echo "$(GREEN)Getting refresh token...$(NC)"; \
	python3 -m venv .venv; \
	.venv/bin/pip install -q google-auth-oauthlib; \
	.venv/bin/python3 << 'PYEOF' \
	from google_auth_oauthlib.flow import InstalledAppFlow; \
	CLIENT_ID = open('.oauth-client-id').read().strip(); \
	CLIENT_SECRET = open('.oauth-client-secret').read().strip(); \
	flow = InstalledAppFlow.from_client_config({ \
	    "installed": { \
	        "client_id": CLIENT_ID, \
	        "client_secret": CLIENT_SECRET, \
	        "auth_uri": "https://accounts.google.com/o/oauth2/auth", \
	        "token_uri": "https://oauth2.googleapis.com/token", \
	    } \
	}, ['https://www.googleapis.com/auth/youtube.readonly']); \
	print("\nOpening browser for authorization..."); \
	credentials = flow.run_local_server(port=8080); \
	with open('.oauth-refresh-token', 'w') as f: \
	    f.write(credentials.refresh_token); \
	print("✅ Refresh token saved"); \
	PYEOF
	@echo "$(GREEN)✅ OAuth credentials obtained$(NC)"

add-secrets:
	@echo "$(GREEN)Adding secrets to GitHub...$(NC)"
	@if [ ! -f .oauth-client-id ] || [ ! -f .oauth-client-secret ] || [ ! -f .oauth-refresh-token ]; then \
		echo "$(RED)Run 'make get-oauth' first$(NC)"; \
		exit 1; \
	fi
	@gh secret set YOUTUBE_CLIENT_ID < .oauth-client-id
	@gh secret set YOUTUBE_CLIENT_SECRET < .oauth-client-secret
	@gh secret set YOUTUBE_REFRESH_TOKEN < .oauth-refresh-token
	@echo "$(GREEN)✅ Secrets added to GitHub$(NC)"
	@echo ""
	@echo "$(YELLOW)Cleaning up local credential files...$(NC)"
	@rm -f .oauth-client-id .oauth-client-secret .oauth-refresh-token .gcloud-project-id
	@echo "$(GREEN)✅ Cleaned up$(NC)"

enable-actions:
	@echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(YELLOW)⚠️  MANUAL STEP REQUIRED$(NC)"
	@echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "You must enable workflow write permissions:"
	@echo ""
	@echo "1. Opening browser to repository settings..."
	@USERNAME=$$(gh api user -q .login); \
	open "https://github.com/$$USERNAME/$(PROJECT_NAME)/settings/actions" 2>/dev/null || \
		echo "   Visit: https://github.com/$$USERNAME/$(PROJECT_NAME)/settings/actions"
	@echo ""
	@echo "2. Scroll down to 'Workflow permissions'"
	@echo "3. Select: 'Read and write permissions'"
	@echo "4. Click 'Save'"
	@echo ""
	@read -p "Press Enter after completing these steps..."
	@echo ""
	@echo "$(GREEN)✅ Ready to trigger sync$(NC)"

trigger-sync:
	@echo "$(GREEN)Triggering first sync...$(NC)"
	@gh workflow run sync.yml
	@echo "$(GREEN)✅ Workflow triggered$(NC)"
	@echo ""
	@echo "Monitor progress with: gh run watch"
	@sleep 5
	@echo ""
	@echo "Waiting for workflow to start..."
	@sleep 10

complete:
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)✅ Setup Complete!$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@USERNAME=$$(gh api user -q .login); \
	echo "$(YELLOW)📱 Bookmark this URL on your phone:$(NC)"; \
	echo "   https://$$USERNAME.github.io/$(PROJECT_NAME)/subscriptions.json"; \
	echo ""; \
	echo "$(YELLOW)📋 View subscription list:$(NC)"; \
	echo "   https://$$USERNAME.github.io/$(PROJECT_NAME)/metadata.json"; \
	echo ""; \
	echo "$(YELLOW)🔍 Check workflow status:$(NC)"; \
	echo "   gh run watch"; \
	echo "   or visit: https://github.com/$$USERNAME/$(PROJECT_NAME)/actions"; \
	echo ""; \
	echo "$(YELLOW)⏰ Auto-sync runs daily at 2 AM UTC$(NC)"; \
	echo ""; \
	echo "$(GREEN)To manually trigger sync:$(NC)"; \
	echo "   gh workflow run sync.yml"; \
	echo ""

# Local development targets

setup-venv:
	@echo "$(GREEN)Setting up Python virtual environment...$(NC)"
	@if [ ! -d .venv ]; then \
		python3 -m venv .venv; \
		echo "$(GREEN)✅ Virtual environment created$(NC)"; \
	else \
		echo "$(YELLOW)Virtual environment already exists$(NC)"; \
	fi
	@echo ""
	@echo "$(GREEN)Installing dependencies...$(NC)"
	@.venv/bin/pip install -q --upgrade pip
	@.venv/bin/pip install -q -r requirements.txt
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

test-local: setup-venv
	@echo "$(GREEN)Running tests...$(NC)"
	@echo ""
	@.venv/bin/pytest
	@echo ""
	@echo "$(GREEN)✅ Tests complete$(NC)"

run-local: setup-venv
	@echo "$(GREEN)Running sync locally...$(NC)"
	@echo ""
	@if [ -z "$$YOUTUBE_CLIENT_ID" ] || [ -z "$$YOUTUBE_CLIENT_SECRET" ] || [ -z "$$YOUTUBE_REFRESH_TOKEN" ]; then \
		echo "$(RED)Error: Required environment variables not set$(NC)"; \
		echo ""; \
		echo "Please set the following environment variables:"; \
		echo "  export YOUTUBE_CLIENT_ID='your-client-id'"; \
		echo "  export YOUTUBE_CLIENT_SECRET='your-client-secret'"; \
		echo "  export YOUTUBE_REFRESH_TOKEN='your-refresh-token'"; \
		echo ""; \
		echo "Or load from a .env file:"; \
		echo "  source .env && make run-local"; \
		exit 1; \
	fi
	@.venv/bin/python3 sync.py
	@echo ""
	@echo "$(GREEN)✅ Sync complete$(NC)"
	@echo ""
	@echo "$(YELLOW)Output files generated in ./output/$(NC)"
	@ls -lh output/

clean-venv:
	@echo "$(YELLOW)Removing virtual environment...$(NC)"
	@rm -rf .venv
	@echo "$(GREEN)✅ Virtual environment removed$(NC)"

clean:
	@echo "$(YELLOW)Cleaning up local files...$(NC)"
	@rm -rf .venv .oauth-* .gcloud-project-id output/
	@echo "$(GREEN)✅ Cleaned$(NC)"

.SILENT: create-files
