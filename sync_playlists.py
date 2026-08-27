#!/usr/bin/env python3
"""
Mirror match-highlight videos from several source playlists into one target playlist.

Runs on a schedule (GitHub Actions). Idempotent: only inserts videos that
aren't already in the target. Safe to re-run.
"""
import os
import re
import sys
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("sync")

# playlist id -> (label, title filter regex or None)
SOURCES = {
    "PLNMKibI54hWU": ("LaLiga",          r"(?i)^.+ vs[.] .+laliga highlights"),
    "PLHue7AF8bVI0": ("Bundesliga",      r"(?i)^.+ vs[.] .+bundesliga highlights"),
    "PLR1b-6EyIaTs": ("Premier League",  r"(?i)^.+ v[.] .+premier league highlights"),
    "PLcS6KNbFQ63k": ("Serie A",         r"(?i)^.+ vs[.] .+extended highlights"),
    "PLWvDauQBKnvI": ("Champions League", r"(?i)^.+ vs[.] .+extended highlights"),
}

# playlistItems.insert costs 50 quota units; the daily cap is 10,000.
# Stay well clear so a big first run spreads over a few days instead of erroring.
MAX_INSERTS_PER_RUN = int(os.environ.get("MAX_INSERTS_PER_RUN", "150"))

# Ignore anything uploaded before this (ISO date). Matches the Pinchflat cutoff.
CUTOFF = os.environ.get("CUTOFF_DATE", "2026-08-15")

# Titles matching this are never added, whatever the per-source regex says.
EXCLUDE = re.compile(r"(?i)first 15 minutes|full match|watch live|press conference")


def client():
    missing = [v for v in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") if not os.environ.get(v)]
    if missing:
        sys.exit("Missing required secrets: " + ", ".join(missing))
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube"],
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def playlist_items(yt, playlist_id):
    """Yield (video_id, title, published_at) for every item in a playlist."""
    page = None
    while True:
        resp = yt.playlistItems().list(
            part="snippet,contentDetails", playlistId=playlist_id,
            maxResults=50, pageToken=page,
        ).execute()
        for item in resp.get("items", []):
            cd, sn = item["contentDetails"], item["snippet"]
            vid = cd.get("videoId")
            if not vid:
                continue
            yield vid, sn.get("title", ""), cd.get("videoPublishedAt", "")
        page = resp.get("nextPageToken")
        if not page:
            return


def main():
    raw = (os.environ.get("YT_TARGET_PLAYLIST") or "").strip()
    if not raw:
        sys.exit("Missing required secret: YT_TARGET_PLAYLIST")
    m = re.search(r"((?:PL|UU|LL|FL|OL)[A-Za-z0-9_-]{10,})", raw)
    if not m:
        sys.exit("YT_TARGET_PLAYLIST holds no playlist id: %d chars, starts %r" % (len(raw), raw[:6]))
    target = m.group(1)
    log.info("resolved target playlist id: %s", target)

    yt = client()

    existing = {vid for vid, _, _ in playlist_items(yt, target)}
    log.info("target playlist already holds %d videos", len(existing))

    queue = []
    for pid, (label, pattern) in SOURCES.items():
        rx = re.compile(pattern) if pattern else None
        kept = skipped = 0
        try:
            for vid, title, published in playlist_items(yt, pid):
                if rx and not rx.search(title):
                    skipped += 1
                    continue
                if EXCLUDE.search(title):
                    skipped += 1
                    continue
                if published and published[:10] < CUTOFF:
                    skipped += 1
                    continue
                if vid in existing:
                    continue
                queue.append((published, vid, label, title))
                kept += 1
        except HttpError as e:
            log.error("%s: could not read playlist %s (%s)", label, pid, e)
            continue
        log.info("%-17s %3d new, %3d filtered out", label, kept, skipped)

    queue.sort()  # oldest first, so the target reads chronologically

    if not queue:
        log.info("nothing to add")
        return

    deferred = max(0, len(queue) - MAX_INSERTS_PER_RUN)
    if deferred:
        log.warning("%d videos queued; inserting %d this run, %d deferred to the next run "
                    "(quota protection)", len(queue), MAX_INSERTS_PER_RUN, deferred)

    added = 0
    for _, vid, label, title in queue[:MAX_INSERTS_PER_RUN]:
        try:
            yt.playlistItems().insert(
                part="snippet",
                body={"snippet": {"playlistId": target,
                                  "resourceId": {"kind": "youtube#video", "videoId": vid}}},
            ).execute()
            added += 1
            log.info("+ [%s] %s", label, title[:80])
        except HttpError as e:
            if "quotaExceeded" in str(e):
                log.error("quota exhausted after %d inserts; the rest will go in tomorrow's run", added)
                break
            log.error("failed to add %s (%s): %s", vid, title[:60], e)

    log.info("done: %d added, %d already present", added, len(existing))


if __name__ == "__main__":
    main()
