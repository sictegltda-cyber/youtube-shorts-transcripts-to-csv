"""
YouTube Shorts: data + transcript + comments in one row, exported to CSV.

Runs an Apify Actor over a channel (or a list of Shorts links) and writes one row per Short
with the video data, the spoken transcript (original language, with timestamps) and the top
comments. Uses only the Python standard library, so there is nothing to install.

Usage:
    set APIFY_TOKEN=apify_api_xxxxxxxx        (Windows)
    export APIFY_TOKEN=apify_api_xxxxxxxx     (Linux/macOS)
    python shorts_a_csv.py https://www.youtube.com/@MrBeast/shorts --max 10 --comments 20 --out shorts.csv

Actors used:
    sicteg/youtube-shorts-scraper     data + transcript + comments
    sicteg/youtube-shorts-transcripts transcript only (cheaper)
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.apify.com/v2"
ACTOR = "sicteg/youtube-shorts-scraper"


def _post(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def _get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def run_actor(token, actor, run_input):
    """Start the Actor and wait for it to finish. Returns the run object."""
    run = _post(f"{API}/acts/{actor.replace('/', '~')}/runs?token={token}", run_input)["data"]
    run_id = run["id"]
    print(f"run {run_id} started ({run['status']})...")
    while True:
        time.sleep(5)
        run = _get(f"{API}/actor-runs/{run_id}?token={token}")["data"]
        if run["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
        print(f"  {run['status']} ...")
    if run["status"] != "SUCCEEDED":
        sys.exit(f"run {run_id} ended as {run['status']}")

    # The charged-event counters keep being written for a few seconds after the run reaches
    # SUCCEEDED, so reading them immediately reports fewer events than were actually delivered.
    time.sleep(8)
    run = _get(f"{API}/actor-runs/{run_id}?token={token}")["data"]

    charged = run.get("chargedEventCounts") or {}
    print(f"run finished in {round(run['stats']['durationMillis'] / 1000)}s")
    print(f"charged events: {json.dumps(charged)}")
    print(f"platform usage: ${run.get('usageTotalUsd', 0):.4f}")
    return run


def export(run, token, out_path):
    items = _get(f"{API}/datasets/{run['defaultDatasetId']}/items?token={token}&clean=true")
    if not items:
        sys.exit("the run returned no rows")

    # Every value is flat on purpose: no nested arrays, so the CSV/Excel import never breaks.
    columns = list(items[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in items:
            writer.writerow({c: ("" if row.get(c) is None else row.get(c)) for c in columns})
    print(f"wrote {len(items)} rows x {len(columns)} columns -> {out_path}")
    return items


def main():
    p = argparse.ArgumentParser(description="YouTube Shorts data + transcripts + comments -> CSV")
    p.add_argument("urls", nargs="+", help="channel URLs, /shorts URLs or Shorts links")
    p.add_argument("--max", type=int, default=10, help="max Shorts per link (default 10)")
    p.add_argument("--comments", type=int, default=20, help="top comments per Short (default 20, 0 = none)")
    p.add_argument("--parallel", type=int, default=4, help="Shorts processed at once, 1-8 (default 4)")
    p.add_argument("--out", default="shorts.csv", help="output CSV path")
    args = p.parse_args()

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("set the APIFY_TOKEN environment variable first")

    run_input = {
        "startUrls": args.urls,
        "maxShortsPorEnlace": args.max,
        "comentariosPorShort": args.comments,
        "incluirTexto": True,
        "enParalelo": args.parallel,
    }
    run = run_actor(token, ACTOR, run_input)
    items = export(run, token, args.out)

    with_text = sum(1 for r in items if r.get("texto_completo"))
    print(f"\n{with_text}/{len(items)} rows have a transcript "
          f"({len(items) - with_text} Shorts have no captions and are not charged)")


if __name__ == "__main__":
    main()
