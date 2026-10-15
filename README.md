# youtube-shorts-transcripts-to-csv

Get **YouTube Shorts data + the spoken transcript + the top comments** in one CSV row per Short —
no API keys of your own, nothing to install, no scraping infrastructure to maintain.

This repository holds a small, dependency-free example script that calls two Apify Actors that do the
heavy part (rotating residential proxies, YouTube's per-IP rate limits, and picking the video's
*original* caption track instead of one of YouTube's ~20 automatic machine translations).

```
python shorts_a_csv.py "https://www.youtube.com/@MrBeast/shorts" --max 50 --comments 20 --out shorts.csv
```

Output: **one row per Short, 20 flat columns** (nothing nested, so CSV/Excel import never breaks):

| Group | Columns |
| --- | --- |
| Video data | `video_id`, `url`, `titulo`, `canal`, `canal_url`, `duracion_s`, `fecha_publicacion`, `vistas`, `me_gusta`, `miniatura_url` |
| Spoken transcript | `idioma`, `subtitulo_automatico`, `es_traduccion`, `fragmentos_total`, `texto_con_tiempos`, `texto_completo` |
| Comments | `comentarios_incluidos`, `comentarios_texto` |
| Status | `estado`, `error` |

## Quick start

You need an Apify account (free plan includes $5 of monthly credit) and its API token.

```bash
# 1. token
export APIFY_TOKEN=apify_api_xxxxxxxx        # Linux/macOS
set APIFY_TOKEN=apify_api_xxxxxxxx           # Windows

# 2. run it (standard library only, Python 3.8+)
python shorts_a_csv.py "https://www.youtube.com/@MrBeast/shorts" \
    --max 50 --comments 20 --parallel 4 --out shorts.csv
```

Any of these inputs work:

```bash
python shorts_a_csv.py "https://www.youtube.com/@MrBeast/shorts"       # a whole channel
python shorts_a_csv.py "https://www.youtube.com/shorts/toIeUtplfWQ"    # one Short
python shorts_a_csv.py https://www.youtube.com/@a/shorts https://www.youtube.com/@b/shorts  # several
```

## The three traps this handles (measured, not guessed)

1. **The transcript you get is usually machine-translated.** The player response for one English Short
   carried 21 caption tracks: the original plus 20 auto-translations. Most tools pick by language
   preference, so you feed an English video in and the text comes out in Spanish or German. This one
   returns the *original* track and exposes `es_traduccion` so you can verify it. Measured: 0 wrongly
   translated rows.
2. **The obvious path costs 1.9 MB per video.** The full watch page is ~1.9 MB; the mobile player
   endpoint returns the same captions at ~340 KB. If you pay for residential proxies per GB, that is
   the difference between profitable and losing money. (The Android client response was 11.9 MB per
   video — 25x the desktop page.)
3. **One IP gets rate-limited after ~30–40 caption requests** and YouTube then answers
   *"sign in to confirm you're not a bot"*. Rotating the proxy per request **and retrying that specific
   error with another IP** took the success rate from 85% to ~95%. On the last full run: 49 of 51 Shorts
   with text, and the retry saved 6 Shorts that would otherwise have come back empty.

## Background: the measurements behind it

We wrote up the three traps with the full numbers on our site:
<https://sictegltda.com/youtube-shorts-transcripts.html>

## What it costs

Pay per result, only for what is actually delivered:

- **$5.00 per 1,000 Shorts** delivered with a transcript
- **$0.20 per 1,000 comments**
- **Shorts without captions are reported (`estado: sin_subtitulo`) and not charged**

The script prints the run's charged events and its platform usage at the end, so you can see exactly
what a run cost. One caveat the script handles for you: the charged-event counters keep being written
for a few seconds after a run reaches `SUCCEEDED`, so reading them immediately shows fewer events than
were delivered — the script waits before printing.

## The Actors

| Actor | What it returns |
| --- | --- |
| [`sicteg/youtube-shorts-scraper`](https://apify.com/sicteg/youtube-shorts-scraper) | Data + transcript + comments (used by this script) |
| [`sicteg/youtube-shorts-transcripts`](https://apify.com/sicteg/youtube-shorts-transcripts) | Transcript + video data only (cheaper, no comments) |

Both are batch Actors: one input JSON in, one dataset out, and they also work through the Apify node in
n8n / Make / Zapier, the Apify MCP server, or any HTTP client.

## Using it from n8n

Add an **Apify** node → *Run Actor and get dataset* → Actor `sicteg/youtube-shorts-scraper`, and paste
the same input the script builds:

```json
{
  "startUrls": ["https://www.youtube.com/@MrBeast/shorts"],
  "maxShortsPorEnlace": 50,
  "comentariosPorShort": 20,
  "incluirTexto": true,
  "enParalelo": 4
}
```

## Notes

- `--max` is a cap **per link**, so several channels in one run multiply it.
- `--comments 0` skips comments entirely and charges nothing for them.
- `enParalelo` (1–8, default 4) is how many Shorts are processed at once; higher is faster and cheaper
  per Short, lower it if YouTube starts rate-limiting your run.
- The CSV is written as UTF-8 with BOM so Excel opens accented text correctly.

MIT licensed. Built and maintained by [SICTEG LTDA](https://apify.com/sicteg) (Colombia).
