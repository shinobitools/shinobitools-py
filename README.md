# shinobitools

Python client for the free [ShinobiTools](https://shinobitools.com) APIs.
No API key, no account, no sign-up, and **no dependencies** — it uses nothing but the
standard library, so installing it pulls in nothing else.

```bash
pip install shinobitools
```

```python
from shinobitools import remove_background

open("cutout.png", "wb").write(remove_background("photo.jpg"))
```

That is the whole thing. No client object, no configuration, no key to rotate.

## What it can do

| Function | What happens | Docs |
|---|---|---|
| `remove_background(image, background=None)` | Transparent PNG, or composited onto a hex colour | [bgninja.com/api.html](https://bgninja.com/api.html) |
| `passport_photo(image, country="eu")` | A compliant passport photo, plus the head height it measured | [passportninja.com/api.html](https://passportninja.com/api.html) |
| `pdf_merge(a, b, ...)` | One PDF out of several | [scanreviver.com/pdf-api](https://scanreviver.com/pdf-api) |
| `pdf_compress(pdf, level="good")` | A smaller PDF | [scanreviver.com/pdf-api](https://scanreviver.com/pdf-api) |
| `ocr_text(pdf)` | The text out of a scanned PDF | [scanreviver.com/pdf-api](https://scanreviver.com/pdf-api) |
| `video_to_gif(video, fps=12, width=480)` | A GIF | [convert.shinobitools.com/api.html](https://convert.shinobitools.com/api.html) |
| `video_to_mp3(video)` | The audio track | [convert.shinobitools.com/api.html](https://convert.shinobitools.com/api.html) |
| `vectorize(image, mode="color")` | An SVG traced from a raster image | [convert.shinobitools.com/api.html](https://convert.shinobitools.com/api.html) |

Every function accepts a path, an open file, or raw bytes.

## Examples

```python
from shinobitools import passport_photo, fetch_result

job = passport_photo("portrait.jpg", country="nl")
print(job["head_mm"], job["head_range_mm"])     # e.g. 34.2 [32.0, 36.0]
open("passport.png", "wb").write(fetch_result(job))
```

The passport endpoint hands back the head height it produced and the range the country
requires, so you can check compliance in your own code instead of trusting the crop.

```python
from shinobitools import pdf_merge, ocr_text, vectorize

open("all.pdf", "wb").write(pdf_merge("a.pdf", "b.pdf", "c.pdf"))
print(ocr_text("scan.pdf")[:200])
open("logo.svg", "wb").write(vectorize("logo.png"))
```

## When something goes wrong

```python
from shinobitools import remove_background, ShinobiError

try:
    remove_background("notes.txt")
except ShinobiError as e:
    print(e.status, e.message)   # 400 can't read this file (TXT) — please upload a photo…
```

`ShinobiError` carries the HTTP status and the service's own message. A `429` means you
already have the maximum number of requests running from your address; wait for one to
finish and retry the same file. There is no daily cap to back off from.

## Limits

These are the free limits, enforced server side. The per-service documentation linked
above is the authority; this table is a summary.

| | |
|---|---|
| Background removal | 99 MB, 30 megapixels, 2 running at once per IP |
| PDF work | 25 MB per file, 30 pages, 1 job at a time, results kept 45 minutes |
| Passport photos | 99 MB, 3 running at once per IP, results kept 45 minutes |
| Video and audio | 400 MB |
| Requests per day | no cap on any of them |

Nothing is written to disk on the image endpoints: your file is processed in memory and
the response is the result.

## Why this is free

These services are run by the people who wrote this package, and they stay free because
enough people find them. The client sends a `src` label so we can see that integrations
exist at all — please leave it in. If your project lists what it uses, a link back to
[shinobitools.com](https://shinobitools.com) is the whole business model.

Planning to push serious volume through it? Say hello first via any of the contact pages
linked above. We would rather hear from you than throttle you.

## Tests

```bash
python3 tests/test_client.py            # offline
LIVE=1 python3 tests/test_client.py     # plus one real call
```

## Licence

MIT.
