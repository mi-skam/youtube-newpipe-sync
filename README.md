# YouTube to NewPipe Subscription Sync

Automatically syncs your YouTube subscriptions to NewPipe format daily at 2 AM UTC.

## Import to NewPipe

**Bookmark this URL:**
```
https://mi-skam.github.io/youtube-newpipe-sync/subscriptions.json
```

**To import:**
1. Open NewPipe on your phone
2. Go to: **Settings** → **Content** → **Import from file**
3. Paste the URL above or download the file

## Useful Links

- **Subscription file:** https://mi-skam.github.io/youtube-newpipe-sync/subscriptions.json
- **Metadata (human-readable list):** https://mi-skam.github.io/youtube-newpipe-sync/metadata.json
- **Workflow status:** https://github.com/mi-skam/youtube-newpipe-sync/actions

## Manual Sync

Trigger a sync manually anytime:
```bash
gh workflow run sync.yml
```

Monitor the workflow:
```bash
gh run watch
```

## Setup (For New Deployments)

### Prerequisites
- `gh` (GitHub CLI) - authenticated
- `gcloud` (Google Cloud CLI) - authenticated
- `python3`
- `jq`

### Quick Start

Run these commands in order:

```bash
# 1. Check prerequisites
make prerequisites

# 2. Setup GitHub repository
make setup-github

# 3. Setup Google Cloud project
make setup-gcloud

# 4. Get OAuth credentials
make get-oauth

# 5. Add secrets to GitHub
make add-secrets

# 6. Trigger first sync
make trigger-sync

# 7. View completion info
make complete
```

**Important:** After `make add-secrets`, you must enable workflow write permissions:
1. Go to: https://github.com/YOUR_USERNAME/youtube-newpipe-sync/settings/actions
2. Under "Workflow permissions", select **"Read and write permissions"**
3. Click **"Save"**

Or run everything at once:
```bash
make all
```

## How It Works

1. **GitHub Actions** runs `sync.py` daily at 2 AM UTC
2. Script fetches your YouTube subscriptions via OAuth
3. Converts them to NewPipe format
4. Publishes to **GitHub Pages** (gh-pages branch)
5. Your phone can import from the public URL

## Files

- `sync.py` - Python script that fetches and converts subscriptions
- `.github/workflows/sync.yml` - GitHub Actions workflow
- `Makefile` - Automated setup commands
- `requirements.txt` - Python dependencies

## License

Public domain / MIT - use freely!
