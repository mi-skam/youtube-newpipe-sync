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

## Cleanup Workflow (Remove Old Subscriptions)

NewPipe's import only **adds** subscriptions - it doesn't remove channels you've unsubscribed from on YouTube. To keep NewPipe in sync:

1. **Import new subscriptions** (adds channels you subscribed to on YouTube)
2. **Visit the cleanup guide:** https://mi-skam.github.io/youtube-newpipe-sync/
3. **Manually unsubscribe** from channels listed in the "Unsubscribe" section

The cleanup guide shows you exactly which channels to remove, with step-by-step instructions.

## Useful Links

- **Cleanup guide (mobile-friendly):** https://mi-skam.github.io/youtube-newpipe-sync/
- **Subscription file (NewPipe):** https://mi-skam.github.io/youtube-newpipe-sync/subscriptions.json
- **Subscription file (YouTube CSV):** https://mi-skam.github.io/youtube-newpipe-sync/subscriptions.csv
- **Changes (JSON):** https://mi-skam.github.io/youtube-newpipe-sync/changes.json
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
3. Compares with previous sync to detect changes (added/removed channels)
4. Generates:
   - `subscriptions.json` - NewPipe import file
   - `subscriptions.csv` - YouTube CSV format (Google Takeout compatible)
   - `index.html` - Mobile-friendly cleanup guide showing which channels to remove
   - `changes.json` - Machine-readable diff
   - `metadata.json` - Stats and channel list
5. Publishes everything to **GitHub Pages** (gh-pages branch)
6. You import new subscriptions and use the cleanup guide to remove old ones

## Files

- `sync.py` - Python script that fetches and converts subscriptions
- `.github/workflows/sync.yml` - GitHub Actions workflow
- `Makefile` - Automated setup commands
- `requirements.txt` - Python dependencies

## License

Public domain / MIT - use freely!
