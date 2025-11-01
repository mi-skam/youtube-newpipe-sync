#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CLIENT_ID = os.environ.get('YOUTUBE_CLIENT_ID')
CLIENT_SECRET = os.environ.get('YOUTUBE_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('YOUTUBE_REFRESH_TOKEN')
OUTPUT_DIR = Path('output')

def get_youtube_client():
    credentials = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    return build('youtube', 'v3', credentials=credentials)

def fetch_all_subscriptions(youtube):
    subscriptions = []
    request = youtube.subscriptions().list(part='snippet', mine=True, maxResults=50)
    while request:
        response = request.execute()
        subscriptions.extend(response['items'])
        request = youtube.subscriptions().list_next(request, response)
    return subscriptions

def transform_to_newpipe_format(subscriptions):
    channels = [{
        'id': s['snippet']['resourceId']['channelId'],
        'name': s['snippet']['title'],
        'url': f"https://www.youtube.com/channel/{s['snippet']['resourceId']['channelId']}"
    } for s in subscriptions]
    return {'app_version': '0.26.1', 'app_version_int': 996, 'subscriptions': channels}

def main():
    print(f"Starting sync at {datetime.utcnow().isoformat()}")
    OUTPUT_DIR.mkdir(exist_ok=True)
    youtube = get_youtube_client()
    print("Fetching subscriptions...")
    subscriptions = fetch_all_subscriptions(youtube)
    print(f"Found {len(subscriptions)} subscriptions")
    newpipe_data = transform_to_newpipe_format(subscriptions)
    with open(OUTPUT_DIR / 'subscriptions.json', 'w', encoding='utf-8') as f:
        json.dump(newpipe_data, f, indent=2, ensure_ascii=False)
    timestamp = datetime.utcnow().strftime('%Y-%m-%d')
    with open(OUTPUT_DIR / f'subscriptions-{timestamp}.json', 'w', encoding='utf-8') as f:
        json.dump(newpipe_data, f, indent=2, ensure_ascii=False)
    metadata = {
        'last_updated': datetime.utcnow().isoformat(),
        'subscription_count': len(subscriptions),
        'channels': [{'name': s['snippet']['title'], 'id': s['snippet']['resourceId']['channelId']} for s in subscriptions]
    }
    with open(OUTPUT_DIR / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print("Sync complete!")

if __name__ == '__main__':
    main()
