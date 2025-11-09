#!/usr/bin/env python3
import csv
import json
import os
from datetime import datetime
from html import escape
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")
OUTPUT_DIR = Path("output")
METADATA_FILE = OUTPUT_DIR / "metadata.json"
TIMELINE_FILE = OUTPUT_DIR / "timeline.json"
MAX_TIMELINE_ENTRIES = 50  # Keep last 50 sync entries


def get_youtube_client():
    credentials = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
    return build("youtube", "v3", credentials=credentials)


def fetch_all_subscriptions(youtube):
    subscriptions = []
    request = youtube.subscriptions().list(part="snippet", mine=True, maxResults=50)
    while request:
        response = request.execute()
        subscriptions.extend(response["items"])
        request = youtube.subscriptions().list_next(request, response)
    return subscriptions


def transform_to_newpipe_format(subscriptions):
    channels = [
        {
            "id": s["snippet"]["resourceId"]["channelId"],
            "name": s["snippet"]["title"],
            "url": f"https://www.youtube.com/channel/{s['snippet']['resourceId']['channelId']}",
        }
        for s in subscriptions
    ]
    return {"app_version": "0.26.1", "app_version_int": 996, "subscriptions": channels}


def transform_to_youtube_csv(subscriptions, output_path):
    """Export subscriptions in YouTube CSV format (Google Takeout compatible)"""
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Channel Id", "Channel Url", "Channel Title"])
        for s in subscriptions:
            channel_id = s["snippet"]["resourceId"]["channelId"]
            channel_url = f"http://www.youtube.com/channel/{channel_id}"
            channel_title = s["snippet"]["title"]
            writer.writerow([channel_id, channel_url, channel_title])


def load_previous_metadata():
    """Load previous metadata if it exists"""
    if METADATA_FILE.exists():
        with open(METADATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return None


def load_timeline():
    """Load timeline history if it exists"""
    if TIMELINE_FILE.exists():
        with open(TIMELINE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"entries": []}


def update_timeline(timeline, changes, metadata):
    """Add a new entry to the timeline and maintain size limit"""
    entry = {
        "timestamp": metadata["last_updated"],
        "subscription_count": metadata["subscription_count"],
        "changes": {
            "added_count": len(changes["added"]),
            "removed_count": len(changes["removed"]),
            "unchanged_count": len(changes["unchanged"]),
            "added_channels": changes["added"],
            "removed_channels": changes["removed"],
        },
    }

    # Only add entry if there are changes or it's the first sync
    if changes["added"] or changes["removed"] or not timeline["entries"]:
        timeline["entries"].append(entry)
        # Keep only the most recent entries
        timeline["entries"] = timeline["entries"][-MAX_TIMELINE_ENTRIES:]

    return timeline


def compare_subscriptions(current_channels, previous_metadata):
    """Compare current subscriptions with previous sync"""
    if not previous_metadata:
        return {"added": current_channels, "removed": [], "unchanged": []}

    previous_channels = {ch["id"]: ch for ch in previous_metadata.get("channels", [])}
    current_channel_ids = {ch["id"] for ch in current_channels}
    previous_channel_ids = set(previous_channels.keys())

    added_ids = current_channel_ids - previous_channel_ids
    removed_ids = previous_channel_ids - current_channel_ids
    unchanged_ids = current_channel_ids & previous_channel_ids

    current_by_id = {ch["id"]: ch for ch in current_channels}

    return {
        "added": [current_by_id[cid] for cid in added_ids],
        "removed": [previous_channels[cid] for cid in removed_ids],
        "unchanged": [current_by_id[cid] for cid in unchanged_ids],
    }


def generate_cleanup_html(changes, metadata, timeline):
    """Generate HTML cleanup guide"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NewPipe Cleanup Guide</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            margin-top: 0;
        }}
        h2 {{
            color: #666;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px;
        }}
        .summary {{
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .stat {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            text-align: center;
            flex: 1;
            min-width: 120px;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .removed {{ color: #d32f2f; }}
        .added {{ color: #388e3c; }}
        .channel {{
            padding: 10px;
            margin: 5px 0;
            background: #fafafa;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .channel-name {{
            font-weight: 500;
        }}
        .channel-link {{
            color: #1976d2;
            text-decoration: none;
            font-size: 0.9em;
        }}
        .empty {{
            color: #999;
            text-align: center;
            padding: 20px;
        }}
        .instructions {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
        }}
        .timestamp {{
            color: #666;
            font-size: 0.9em;
        }}
        .timeline {{
            margin-top: 20px;
        }}
        .timeline-entry {{
            border-left: 3px solid #1976d2;
            padding: 15px;
            margin: 15px 0;
            background: #fafafa;
            border-radius: 0 4px 4px 0;
        }}
        .timeline-entry.no-changes {{
            border-left-color: #999;
            opacity: 0.7;
        }}
        .timeline-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .timeline-date {{
            font-weight: bold;
            color: #333;
        }}
        .timeline-stats {{
            display: flex;
            gap: 15px;
            font-size: 0.9em;
        }}
        .timeline-detail {{
            margin-top: 10px;
            font-size: 0.9em;
        }}
        .timeline-channels {{
            margin-top: 8px;
            padding-left: 20px;
        }}
        .hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>📱 NewPipe Cleanup Guide</h1>
        <p class="timestamp">Last updated: {metadata["last_updated"]}</p>

        <div class="summary">
            <div class="stat">
                <div class="stat-number">{metadata["subscription_count"]}</div>
                <div class="stat-label">Total Subscriptions</div>
            </div>
            <div class="stat">
                <div class="stat-number added">{len(changes["added"])}</div>
                <div class="stat-label">Added</div>
            </div>
            <div class="stat">
                <div class="stat-number removed">{len(changes["removed"])}</div>
                <div class="stat-label">Removed</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>📥 Step 1: Import New Subscriptions</h2>
        <div class="instructions">
            <strong>Import this file to add new YouTube subscriptions to NewPipe:</strong>
        </div>
        <div style="background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 15px 0; word-break: break-all;">
            <strong>NewPipe Format:</strong><br>
            <a href="subscriptions.json" style="color: #1976d2;">subscriptions.json</a><br><br>
            <strong>YouTube CSV Format (Google Takeout compatible):</strong><br>
            <a href="subscriptions.csv" style="color: #1976d2;">subscriptions.csv</a>
        </div>
        <div style="padding-left: 20px;">
            <strong>How to import (NewPipe):</strong>
            <ol>
                <li>Open NewPipe on your phone</li>
                <li>Tap the ☰ menu (top-left)</li>
                <li>Go to <strong>Settings</strong> → <strong>Content</strong></li>
                <li>Tap <strong>Import from file</strong></li>
                <li>Paste the URL above or download and select the file</li>
                <li>Tap <strong>Import</strong></li>
            </ol>
            <p style="color: #666; font-size: 0.9em;">
                💡 <em>Tip: Bookmark the subscriptions.json URL for easy access!</em><br>
                📊 <em>The CSV format can be imported into YouTube or other compatible apps.</em>
            </p>
        </div>
    </div>
"""

    if changes["removed"]:
        html += """
    <div class="card">
        <h2 class="removed">❌ Step 2: Remove Old Subscriptions</h2>
        <div class="instructions">
            <strong>These channels were removed from your YouTube subscriptions.</strong><br>
            To clean up NewPipe, manually unsubscribe from each channel below:
            <ol>
                <li>Open NewPipe</li>
                <li>Tap the <strong>Subscriptions</strong> tab</li>
                <li><strong>Long-press</strong> the channel</li>
                <li>Select <strong>Unsubscribe</strong></li>
            </ol>
        </div>
"""
        for channel in sorted(changes["removed"], key=lambda x: x["name"]):
            html += f"""
        <div class="channel">
            <span class="channel-name">{escape(channel["name"])}</span>
            <a href="https://www.youtube.com/channel/{escape(channel["id"])}" class="channel-link" target="_blank">View</a>
        </div>"""
        html += "\n    </div>"
    else:
        html += """
    <div class="card">
        <h2>✅ No Cleanup Needed</h2>
        <p class="empty">All your NewPipe subscriptions match YouTube!</p>
    </div>"""

    if changes["added"]:
        html += """
    <div class="card">
        <h2 class="added">✨ New Channels Added</h2>
        <p>These channels are new since your last sync. They'll be added when you import subscriptions.json above:</p>
"""
        for channel in sorted(changes["added"], key=lambda x: x["name"]):
            html += f"""
        <div class="channel">
            <span class="channel-name">{escape(channel["name"])}</span>
            <a href="https://www.youtube.com/channel/{escape(channel["id"])}" class="channel-link" target="_blank">View</a>
        </div>"""
        html += "\n    </div>"

    # Add timeline section
    html += """
    <div class="card">
        <h2>📅 Change Timeline</h2>
        <p>History of subscription changes over time:</p>
        <div class="timeline">
"""

    # Display timeline entries in reverse chronological order (most recent first)
    if timeline.get("entries"):
        # Show only last 10 entries by default
        displayed_entries = timeline["entries"][-10:]
        for entry in reversed(displayed_entries):
            timestamp = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")).strftime(
                "%Y-%m-%d %H:%M UTC"
            )
            changes_info = entry["changes"]
            has_changes = changes_info["added_count"] > 0 or changes_info["removed_count"] > 0

            entry_class = "timeline-entry" if has_changes else "timeline-entry no-changes"

            html += f"""
            <div class="{entry_class}">
                <div class="timeline-header">
                    <span class="timeline-date">{timestamp}</span>
                    <div class="timeline-stats">
                        <span>📊 {entry["subscription_count"]} total</span>
"""
            if has_changes:
                html += f"""                        <span class="added">+{changes_info["added_count"]}</span>
                        <span class="removed">-{changes_info["removed_count"]}</span>
"""
            else:
                html += """                        <span style="color: #999;">No changes</span>
"""

            html += """                    </div>
                </div>
"""

            # Show added channels if any
            if changes_info["added_count"] > 0:
                html += f"""
                <div class="timeline-detail">
                    <strong class="added">Added {changes_info["added_count"]} channel(s):</strong>
                    <div class="timeline-channels">
"""
                for channel in changes_info["added_channels"][:5]:  # Show first 5
                    html += f"""                        • {escape(channel["name"])}<br>
"""
                if changes_info["added_count"] > 5:
                    html += f"""                        <em>... and {changes_info["added_count"] - 5} more</em><br>
"""
                html += """                    </div>
                </div>
"""

            # Show removed channels if any
            if changes_info["removed_count"] > 0:
                html += f"""
                <div class="timeline-detail">
                    <strong class="removed">Removed {changes_info["removed_count"]} channel(s):</strong>
                    <div class="timeline-channels">
"""
                for channel in changes_info["removed_channels"][:5]:  # Show first 5
                    html += f"""                        • {escape(channel["name"])}<br>
"""
                if changes_info["removed_count"] > 5:
                    html += f"""                        <em>... and {changes_info["removed_count"] - 5} more</em><br>
"""
                html += """                    </div>
                </div>
"""

            html += """            </div>
"""

        # Show message if there are more entries
        if len(timeline["entries"]) > 10:
            html += f"""
            <p class="empty" style="margin-top: 20px;">
                Showing last 10 of {len(timeline["entries"])} sync events.
                Full history is preserved in timeline.json.
            </p>
"""
    else:
        html += """
            <p class="empty">No previous syncs recorded yet. This will build up over time!</p>
"""

    html += """        </div>
    </div>

</body>
</html>"""
    return html


def main():
    print(f"Starting sync at {datetime.utcnow().isoformat()}")
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load previous metadata for comparison
    print("Loading previous sync data...")
    previous_metadata = load_previous_metadata()

    # Load timeline history
    print("Loading timeline history...")
    timeline = load_timeline()

    # Fetch current YouTube subscriptions
    youtube = get_youtube_client()
    print("Fetching subscriptions...")
    subscriptions = fetch_all_subscriptions(youtube)
    print(f"Found {len(subscriptions)} subscriptions")

    # Transform to NewPipe format
    newpipe_data = transform_to_newpipe_format(subscriptions)

    # Create channel list for comparison
    current_channels = [
        {"name": s["snippet"]["title"], "id": s["snippet"]["resourceId"]["channelId"]}
        for s in subscriptions
    ]

    # Compare with previous sync
    print("Comparing with previous sync...")
    changes = compare_subscriptions(current_channels, previous_metadata)

    print(f"  Added: {len(changes['added'])}")
    print(f"  Removed: {len(changes['removed'])}")
    print(f"  Unchanged: {len(changes['unchanged'])}")

    # Save subscriptions.json
    with open(OUTPUT_DIR / "subscriptions.json", "w", encoding="utf-8") as f:
        json.dump(newpipe_data, f, indent=2, ensure_ascii=False)

    # Save timestamped backup
    timestamp = datetime.utcnow().strftime("%Y-%m-%d")
    with open(
        OUTPUT_DIR / f"subscriptions-{timestamp}.json", "w", encoding="utf-8"
    ) as f:
        json.dump(newpipe_data, f, indent=2, ensure_ascii=False)

    # Export YouTube CSV format
    print("Generating YouTube CSV export...")
    transform_to_youtube_csv(subscriptions, OUTPUT_DIR / "subscriptions.csv")
    transform_to_youtube_csv(
        subscriptions, OUTPUT_DIR / f"subscriptions-{timestamp}.csv"
    )

    # Create metadata with change tracking
    metadata = {
        "last_updated": datetime.utcnow().isoformat(),
        "subscription_count": len(subscriptions),
        "changes": {
            "added_count": len(changes["added"]),
            "removed_count": len(changes["removed"]),
            "unchanged_count": len(changes["unchanged"]),
        },
        "channels": current_channels,
    }

    if previous_metadata:
        metadata["previous_sync"] = previous_metadata.get("last_updated")

    # Save metadata.json
    with open(OUTPUT_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Update and save timeline
    print("Updating timeline...")
    timeline = update_timeline(timeline, changes, metadata)
    with open(TIMELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)

    # Save changes.json
    print("Generating changes file...")
    with open(OUTPUT_DIR / "changes.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "sync_date": datetime.utcnow().isoformat(),
                "previous_sync": previous_metadata.get("last_updated")
                if previous_metadata
                else None,
                "changes": changes,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    # Generate cleanup HTML guide as index.html
    print("Generating cleanup guide...")
    cleanup_html = generate_cleanup_html(changes, metadata, timeline)
    with open(OUTPUT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(cleanup_html)

    print("Sync complete!")
    if changes["removed"]:
        print(
            f"⚠️  {len(changes['removed'])} channel(s) need to be removed from NewPipe"
        )
        print("   View index.html for details")


if __name__ == "__main__":
    main()
