#!/usr/bin/env python3

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "youtube-playlist-to-slack"
AUTH_FILE = CONFIG_DIR / "auth.json"
CONFIG_FILE = CONFIG_DIR / "config.json"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
CHANNELS_DIR = CONFIG_DIR / "channels"

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
PLAYLIST_ID = "LL"

YOUTUBE_VIDEO_RE = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})")


def load_credentials() -> Credentials:
    if not AUTH_FILE.exists():
        raw = json.loads(CREDENTIALS_FILE.read_text())
        client = raw.get("installed") or raw.get("web", {})
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)
        _save_auth(creds, client["client_id"], client["client_secret"])
        return creds

    data = json.loads(AUTH_FILE.read_text())
    creds = Credentials(
        token=data.get("access_token"),
        refresh_token=data["refresh_token"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
        expiry=datetime.fromisoformat(data["expiry"]) if data.get("expiry") else None,
    )
    if not creds.valid:
        creds.refresh(Request())
        _save_auth(creds, data["client_id"], data["client_secret"])
    return creds


def _save_auth(creds: Credentials, client_id: str, client_secret: str):
    AUTH_FILE.write_text(json.dumps({
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }, indent=2))


def fetch_playlist_video_ids(creds: Credentials) -> list[str]:
    resp = httpx.get(
        "https://www.googleapis.com/youtube/v3/playlistItems",
        headers={"Authorization": f"Bearer {creds.token}"},
        params={"part": "snippet", "playlistId": PLAYLIST_ID, "maxResults": 20},
    )
    resp.raise_for_status()
    return [item["snippet"]["resourceId"]["videoId"] for item in resp.json().get("items", [])]


def channel_data_file(workspace: str, channel: str) -> Path:
    return CHANNELS_DIR / workspace / f"{channel}.json"


def load_channel_data(workspace: str, channel: str) -> dict | None:
    path = channel_data_file(workspace, channel)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_channel_data(workspace: str, channel: str, data: dict):
    path = channel_data_file(workspace, channel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def sync_channel_messages(workspace: str, channel: str, data: dict) -> bool:
    result = subprocess.run(
        ["agent-slack", "message", "list", f"#{channel}",
         "--workspace", workspace, "--limit", "100"],
        capture_output=True, text=True, check=True,
    )
    dirty = False
    for msg in json.loads(result.stdout).get("messages", []):
        ts = msg["ts"]
        if ts in data["messages"]:
            continue
        video_id = next(iter(YOUTUBE_VIDEO_RE.findall(msg.get("content", ""))), None)
        if not video_id:
            continue
        sent_at = datetime.fromtimestamp(float(ts)).isoformat()
        data["messages"][ts] = {
            "user_id": msg.get("author", {}).get("user_id"),
            "sent_at": sent_at,
            "video_id": video_id,
        }
        if video_id not in data["videos"]:
            data["videos"][video_id] = {"added_at": sent_at, "message_ts": ts}
        dirty = True
    return dirty


def send_to_slack(video_id: str, workspace: str, channel: str):
    subprocess.run(
        ["agent-slack", "message", "send", "--workspace", workspace,
         f"#{channel}", f"https://www.youtube.com/watch?v={video_id}"],
        check=True,
    )


def main():
    config = json.loads(CONFIG_FILE.read_text())
    workspace = config["slack_workspace"]
    channel = config["slack_channel"]

    data = load_channel_data(workspace, channel)
    is_first_run = data is None
    if data is None:
        data = {"messages": {}, "videos": {}}
    dirty = sync_channel_messages(workspace, channel, data)

    creds = load_credentials()
    video_ids = fetch_playlist_video_ids(creds)

    new_ids = [vid for vid in video_ids if vid not in data["videos"]]
    if new_ids:
        for video_id in reversed(new_ids):
            if not is_first_run:
                send_to_slack(video_id, workspace, channel)
            data["videos"][video_id] = {"added_at": datetime.now().isoformat(), "message_ts": None}
        dirty = True

    if dirty:
        save_channel_data(workspace, channel, data)


if __name__ == "__main__":
    main()
