import csv
import json

import pytest

from sync import (
    compare_subscriptions,
    generate_cleanup_html,
    load_previous_metadata,
    load_timeline,
    transform_to_newpipe_format,
    transform_to_youtube_csv,
    update_timeline,
)


@pytest.fixture
def sample_subscriptions():
    """Sample YouTube API subscriptions data"""
    return [
        {"snippet": {"title": "Tech Channel", "resourceId": {"channelId": "UC123"}}},
        {"snippet": {"title": "Gaming Channel", "resourceId": {"channelId": "UC456"}}},
    ]


@pytest.fixture
def sample_channels():
    """Sample channel list for comparison"""
    return [
        {"name": "Tech Channel", "id": "UC123"},
        {"name": "Gaming Channel", "id": "UC456"},
    ]


class TestTransformToNewpipeFormat:
    """Tests for transform_to_newpipe_format function"""

    def test_transform_basic(self, sample_subscriptions):
        """Test basic transformation to NewPipe format"""
        result = transform_to_newpipe_format(sample_subscriptions)

        assert "app_version" in result
        assert "app_version_int" in result
        assert "subscriptions" in result
        assert len(result["subscriptions"]) == 2

    def test_transform_channel_structure(self, sample_subscriptions):
        """Test that each channel has correct structure"""
        result = transform_to_newpipe_format(sample_subscriptions)

        for channel in result["subscriptions"]:
            assert "id" in channel
            assert "name" in channel
            assert "url" in channel

    def test_transform_channel_data(self, sample_subscriptions):
        """Test that channel data is correctly mapped"""
        result = transform_to_newpipe_format(sample_subscriptions)

        first_channel = result["subscriptions"][0]
        assert first_channel["id"] == "UC123"
        assert first_channel["name"] == "Tech Channel"
        assert first_channel["url"] == "https://www.youtube.com/channel/UC123"

    def test_transform_empty_list(self):
        """Test transformation with empty subscriptions list"""
        result = transform_to_newpipe_format([])

        assert result["subscriptions"] == []
        assert result["app_version"] == "0.26.1"


class TestTransformToYoutubeCsv:
    """Tests for transform_to_youtube_csv function"""

    def test_csv_creation(self, sample_subscriptions, tmp_path):
        """Test that CSV file is created with correct headers"""
        output_path = tmp_path / "test.csv"
        transform_to_youtube_csv(sample_subscriptions, output_path)

        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert headers == ["Channel Id", "Channel Url", "Channel Title"]

    def test_csv_content(self, sample_subscriptions, tmp_path):
        """Test that CSV contains correct data"""
        output_path = tmp_path / "test.csv"
        transform_to_youtube_csv(sample_subscriptions, output_path)

        with open(output_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # Skip headers
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0][0] == "UC123"
        assert rows[0][1] == "http://www.youtube.com/channel/UC123"
        assert rows[0][2] == "Tech Channel"

    def test_csv_empty_subscriptions(self, tmp_path):
        """Test CSV creation with empty subscriptions"""
        output_path = tmp_path / "test.csv"
        transform_to_youtube_csv([], output_path)

        with open(output_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

        assert headers == ["Channel Id", "Channel Url", "Channel Title"]
        assert len(rows) == 0


class TestCompareSubscriptions:
    """Tests for compare_subscriptions function"""

    def test_compare_no_previous_metadata(self, sample_channels):
        """Test comparison when no previous metadata exists"""
        result = compare_subscriptions(sample_channels, None)

        assert result["added"] == sample_channels
        assert result["removed"] == []
        assert result["unchanged"] == []

    def test_compare_no_changes(self, sample_channels):
        """Test comparison when nothing changed"""
        previous_metadata = {"channels": sample_channels}
        result = compare_subscriptions(sample_channels, previous_metadata)

        assert result["added"] == []
        assert result["removed"] == []
        assert len(result["unchanged"]) == 2

    def test_compare_added_channels(self, sample_channels):
        """Test detection of newly added channels"""
        previous_channels = [sample_channels[0]]
        previous_metadata = {"channels": previous_channels}

        result = compare_subscriptions(sample_channels, previous_metadata)

        assert len(result["added"]) == 1
        assert result["added"][0]["id"] == "UC456"
        assert result["removed"] == []
        assert len(result["unchanged"]) == 1

    def test_compare_removed_channels(self, sample_channels):
        """Test detection of removed channels"""
        current_channels = [sample_channels[0]]
        previous_metadata = {"channels": sample_channels}

        result = compare_subscriptions(current_channels, previous_metadata)

        assert result["added"] == []
        assert len(result["removed"]) == 1
        assert result["removed"][0]["id"] == "UC456"
        assert len(result["unchanged"]) == 1

    def test_compare_mixed_changes(self):
        """Test with both added and removed channels"""
        previous_channels = [
            {"name": "Old Channel", "id": "UC111"},
            {"name": "Tech Channel", "id": "UC123"},
        ]
        current_channels = [
            {"name": "Tech Channel", "id": "UC123"},
            {"name": "New Channel", "id": "UC999"},
        ]
        previous_metadata = {"channels": previous_channels}

        result = compare_subscriptions(current_channels, previous_metadata)

        assert len(result["added"]) == 1
        assert result["added"][0]["id"] == "UC999"
        assert len(result["removed"]) == 1
        assert result["removed"][0]["id"] == "UC111"
        assert len(result["unchanged"]) == 1
        assert result["unchanged"][0]["id"] == "UC123"


class TestGenerateCleanupHtml:
    """Tests for generate_cleanup_html function"""

    def test_html_generation_basic(self):
        """Test that HTML is generated with basic structure"""
        changes = {"added": [], "removed": [], "unchanged": []}
        metadata = {"last_updated": "2025-01-01T00:00:00", "subscription_count": 0}
        timeline = {"entries": []}

        html = generate_cleanup_html(changes, metadata, timeline)

        assert "<!DOCTYPE html>" in html
        assert "NewPipe Cleanup Guide" in html
        assert "2025-01-01" in html
        assert "Change Timeline" in html

    def test_html_with_removed_channels(self):
        """Test HTML generation with removed channels"""
        changes = {
            "added": [],
            "removed": [{"name": "Removed Channel", "id": "UC999"}],
            "unchanged": [],
        }
        metadata = {"last_updated": "2025-01-01T00:00:00", "subscription_count": 1}
        timeline = {"entries": []}

        html = generate_cleanup_html(changes, metadata, timeline)

        assert "Remove Old Subscriptions" in html
        assert "Removed Channel" in html
        assert "UC999" in html

    def test_html_with_added_channels(self):
        """Test HTML generation with added channels"""
        changes = {
            "added": [{"name": "New Channel", "id": "UC888"}],
            "removed": [],
            "unchanged": [],
        }
        metadata = {"last_updated": "2025-01-01T00:00:00", "subscription_count": 1}
        timeline = {"entries": []}

        html = generate_cleanup_html(changes, metadata, timeline)

        assert "New Channels Added" in html
        assert "New Channel" in html
        assert "UC888" in html

    def test_html_no_cleanup_needed(self):
        """Test HTML when no cleanup is needed"""
        changes = {
            "added": [],
            "removed": [],
            "unchanged": [{"name": "Existing Channel", "id": "UC123"}],
        }
        metadata = {"last_updated": "2025-01-01T00:00:00", "subscription_count": 1}
        timeline = {"entries": []}

        html = generate_cleanup_html(changes, metadata, timeline)

        assert "No Cleanup Needed" in html

    def test_html_with_timeline_entries(self):
        """Test HTML generation with timeline entries"""
        changes = {"added": [], "removed": [], "unchanged": []}
        metadata = {"last_updated": "2025-01-01T00:00:00", "subscription_count": 5}
        timeline = {
            "entries": [
                {
                    "timestamp": "2025-01-01T00:00:00",
                    "subscription_count": 5,
                    "changes": {
                        "added_count": 2,
                        "removed_count": 1,
                        "unchanged_count": 2,
                        "added_channels": [{"name": "New Channel", "id": "UC123"}],
                        "removed_channels": [{"name": "Old Channel", "id": "UC456"}],
                    },
                }
            ]
        }

        html = generate_cleanup_html(changes, metadata, timeline)

        assert "Change Timeline" in html
        assert "New Channel" in html
        assert "Old Channel" in html


class TestLoadPreviousMetadata:
    """Tests for load_previous_metadata function"""

    def test_load_nonexistent_metadata(self, tmp_path, monkeypatch):
        """Test loading when metadata file doesn't exist"""
        monkeypatch.setattr("sync.METADATA_FILE", tmp_path / "nonexistent.json")

        result = load_previous_metadata()

        assert result is None

    def test_load_existing_metadata(self, tmp_path, monkeypatch):
        """Test loading existing metadata file"""
        metadata_file = tmp_path / "metadata.json"
        test_data = {
            "last_updated": "2025-01-01T00:00:00",
            "subscription_count": 5,
            "channels": [],
        }

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        monkeypatch.setattr("sync.METADATA_FILE", metadata_file)
        result = load_previous_metadata()

        assert result == test_data
        assert result["subscription_count"] == 5


class TestLoadTimeline:
    """Tests for load_timeline function"""

    def test_load_nonexistent_timeline(self, tmp_path, monkeypatch):
        """Test loading when timeline file doesn't exist"""
        monkeypatch.setattr("sync.TIMELINE_FILE", tmp_path / "nonexistent.json")

        result = load_timeline()

        assert result == {"entries": []}

    def test_load_existing_timeline(self, tmp_path, monkeypatch):
        """Test loading existing timeline file"""
        timeline_file = tmp_path / "timeline.json"
        test_data = {
            "entries": [
                {
                    "timestamp": "2025-01-01T00:00:00",
                    "subscription_count": 5,
                    "changes": {
                        "added_count": 2,
                        "removed_count": 1,
                        "unchanged_count": 2,
                        "added_channels": [],
                        "removed_channels": [],
                    },
                }
            ]
        }

        with open(timeline_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        monkeypatch.setattr("sync.TIMELINE_FILE", timeline_file)
        result = load_timeline()

        assert result == test_data
        assert len(result["entries"]) == 1


class TestUpdateTimeline:
    """Tests for update_timeline function"""

    def test_update_empty_timeline_with_changes(self):
        """Test updating empty timeline with changes"""
        timeline = {"entries": []}
        changes = {
            "added": [{"name": "New Channel", "id": "UC123"}],
            "removed": [],
            "unchanged": [],
        }
        metadata = {
            "last_updated": "2025-01-01T00:00:00",
            "subscription_count": 1,
        }

        result = update_timeline(timeline, changes, metadata)

        assert len(result["entries"]) == 1
        assert result["entries"][0]["timestamp"] == "2025-01-01T00:00:00"
        assert result["entries"][0]["subscription_count"] == 1
        assert result["entries"][0]["changes"]["added_count"] == 1

    def test_update_timeline_no_changes(self):
        """Test that timeline doesn't add entry when there are no changes"""
        timeline = {
            "entries": [
                {
                    "timestamp": "2025-01-01T00:00:00",
                    "subscription_count": 5,
                    "changes": {
                        "added_count": 0,
                        "removed_count": 0,
                        "unchanged_count": 5,
                        "added_channels": [],
                        "removed_channels": [],
                    },
                }
            ]
        }
        changes = {"added": [], "removed": [], "unchanged": [{"name": "Ch1", "id": "UC1"}]}
        metadata = {
            "last_updated": "2025-01-02T00:00:00",
            "subscription_count": 1,
        }

        result = update_timeline(timeline, changes, metadata)

        # Should not add a new entry since there are no changes and timeline is not empty
        assert len(result["entries"]) == 1

    def test_update_timeline_first_entry(self):
        """Test that first sync is always added even without changes"""
        timeline = {"entries": []}
        changes = {"added": [], "removed": [], "unchanged": [{"name": "Ch1", "id": "UC1"}]}
        metadata = {
            "last_updated": "2025-01-01T00:00:00",
            "subscription_count": 1,
        }

        result = update_timeline(timeline, changes, metadata)

        # First entry should always be added
        assert len(result["entries"]) == 1

    def test_update_timeline_max_entries(self, monkeypatch):
        """Test that timeline maintains max entry limit"""
        # Set a small max for testing
        monkeypatch.setattr("sync.MAX_TIMELINE_ENTRIES", 3)

        timeline = {"entries": []}
        metadata_base = {
            "last_updated": "2025-01-01T00:00:00",
            "subscription_count": 1,
        }

        # Add 5 entries
        for i in range(5):
            changes = {
                "added": [{"name": f"Channel {i}", "id": f"UC{i}"}],
                "removed": [],
                "unchanged": [],
            }
            metadata_base["last_updated"] = f"2025-01-0{i+1}T00:00:00"
            timeline = update_timeline(timeline, changes, metadata_base)

        # Should only keep last 3 entries
        assert len(timeline["entries"]) == 3
        # Verify it kept the most recent ones
        assert "Channel 2" in str(timeline["entries"][0])
        assert "Channel 4" in str(timeline["entries"][-1])
