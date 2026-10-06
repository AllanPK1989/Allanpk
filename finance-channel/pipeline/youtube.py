"""Upload to YouTube with the Data API v3.

Credentials come from three environment variables (GitHub secrets):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
The refresh token decides which channel the video lands on, so each channel
names its own (publish.refresh_token_env: YT_EN_REFRESH_TOKEN for English).
See docs/SETUP.md for how to create them.

Note: until your Google Cloud project passes YouTube's API audit, YouTube
forces every API upload to private and locks it. Keep publish.mode: manual
in config.yaml until the audit is approved.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _token_env() -> str:
    from .config import config
    return config()["publish"].get("refresh_token_env", "YT_REFRESH_TOKEN")


def configured() -> bool:
    return all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", _token_env()))


def _service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        None,
        refresh_token=os.environ[_token_env()],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(video: Path, body: dict, thumbnail: Path | None = None) -> str:
    """Resumable upload; returns the new video id."""
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    yt = _service()
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media, notifySubscribers=True)
    resp, retries = None, 0
    while resp is None:
        try:
            _, resp = req.next_chunk()
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and retries < 6:
                retries += 1
                time.sleep(2 ** retries)
                continue
            raise
    vid = resp["id"]
    if thumbnail and thumbnail.exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumbnail), mimetype="image/png")).execute()
        except HttpError as e:
            # Custom thumbnails need a phone-verified channel; the video is fine without one.
            print(f"warning: thumbnail not set ({e.resp.status}); verify your channel at youtube.com/verify")
    return vid
