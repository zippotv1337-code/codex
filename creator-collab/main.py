from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import higgsfield_client
from dotenv import load_dotenv
from higgsfield_client import Cancelled, Completed, Failed, NSFW, Status

from creator_ops.secrets import get_secret

MODEL = "bytedance/seedance-2.5/text-to-video"


def _video_url(result: dict[str, Any]) -> str | None:
    video = result.get("video")
    if isinstance(video, str):
        return video
    if isinstance(video, dict):
        url = video.get("url")
        return url if isinstance(url, str) and url else None
    return None


def main() -> int:
    credential = get_secret("HF_KEY", worker="media-higgsfield")
    if not credential or ":" not in credential:
        print("HF_KEY is missing or invalid in the Zippoworkz secret store.", file=sys.stderr)
        return 2

    terminal: list[Status] = []

    def remember_terminal(status: Status) -> None:
        if isinstance(status, (Completed, Failed, Cancelled, NSFW)):
            terminal[:] = [status]

    try:
        result = higgsfield_client.subscribe(
            MODEL,
            arguments={
                "prompt": "A cinematic scene at sunset",
                "duration": 5,
                "resolution": "720p",
                "aspect_ratio": "16:9",
            },
            on_queue_update=remember_terminal,
        )
    except Exception as exc:
        cause = getattr(exc, "__cause__", None)
        response = getattr(cause, "response", None)
        code = getattr(response, "status_code", None)
        suffix = f", HTTP {code}" if code is not None else ""
        print(
            f"Higgsfield request failed ({type(exc).__name__}{suffix}).",
            file=sys.stderr,
        )
        return 1
    status = terminal[0] if terminal else None
    if isinstance(status, Failed):
        print("Generation failed.", file=sys.stderr)
        return 1
    if isinstance(status, Cancelled):
        print("Generation was canceled.", file=sys.stderr)
        return 1
    if isinstance(status, NSFW):
        print("Generation was moderated.", file=sys.stderr)
        return 1
    if not isinstance(status, Completed):
        print("Generation did not confirm completion.", file=sys.stderr)
        return 1

    url = _video_url(result)
    if not url:
        print("Completed response did not contain a video URL.", file=sys.stderr)
        return 1

    print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
