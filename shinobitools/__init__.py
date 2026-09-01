"""Thin Python client for the free ShinobiTools APIs.

No API key, no account, no dependencies. Every function takes a path (or bytes) and
returns bytes or a dict, so you can drop it into a script without thinking about it.

    from shinobitools import remove_background
    open("out.png", "wb").write(remove_background("photo.jpg"))

Docs for the underlying HTTP APIs:
    https://bgninja.com/api.html                background removal
    https://scanreviver.com/pdf-api             PDF work and OCR
    https://passportninja.com/api.html          passport photos
    https://convert.shinobitools.com/api.html   video, audio and vector

The services are free within published limits and are run by the people who wrote this
package. If this ends up in something you build, a link back is the whole business model.
"""
from __future__ import annotations

import json
import mimetypes
import os
import urllib.error
import urllib.request
import uuid

__version__ = "0.1.0"
__all__ = [
    "remove_background", "passport_photo", "pdf_merge", "pdf_compress",
    "ocr_text", "video_to_gif", "video_to_mp3", "vectorize",
    "ShinobiError", "SRC",
]

# Identifies this package to the service. It is the only way we can tell that an
# integration exists, which is what keeps the APIs worth running. Please leave it.
SRC = "shinobitools-py"

BGNINJA = "https://bgninja.com"
SCANREVIVER = "https://scanreviver.com"
PASSPORTNINJA = "https://passportninja.com"
CONVERT = "https://convert.shinobitools.com"

TIMEOUT = 300


class ShinobiError(RuntimeError):
    """The service refused the request. `status` is the HTTP code, `message` its reason."""

    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message


def _bytes_van(bestand) -> tuple[bytes, str]:
    """Accepteert een pad, een open bestand of kale bytes. Geeft (inhoud, naam)."""
    if isinstance(bestand, (bytes, bytearray)):
        return bytes(bestand), "upload"
    if hasattr(bestand, "read"):
        inhoud = bestand.read()
        return inhoud, os.path.basename(getattr(bestand, "name", "upload"))
    with open(bestand, "rb") as f:
        return f.read(), os.path.basename(str(bestand))


def _multipart(velden: dict, bestanden: list[tuple[str, bytes, str]]) -> tuple[bytes, str]:
    """Bouwt een multipart/form-data-body met alleen de standaardbibliotheek.

    Bewust geen `requests`: dit pakket heeft nul afhankelijkheden, en dat is voor een
    kleine client een echte eigenschap — wie het installeert krijgt niets anders mee.
    """
    grens = f"----shinobitools{uuid.uuid4().hex}"
    delen: list[bytes] = []
    for naam, waarde in velden.items():
        if waarde is None:
            continue
        delen.append(
            f"--{grens}\r\nContent-Disposition: form-data; name=\"{naam}\"\r\n\r\n"
            f"{waarde}\r\n".encode()
        )
    for naam, inhoud, bestandsnaam in bestanden:
        soort = mimetypes.guess_type(bestandsnaam)[0] or "application/octet-stream"
        delen.append(
            f"--{grens}\r\nContent-Disposition: form-data; "
            f"name=\"{naam}\"; filename=\"{bestandsnaam}\"\r\n"
            f"Content-Type: {soort}\r\n\r\n".encode()
        )
        delen.append(inhoud)
        delen.append(b"\r\n")
    delen.append(f"--{grens}--\r\n".encode())
    return b"".join(delen), f"multipart/form-data; boundary={grens}"


# Cloudflare weigert urllib's standaard User-Agent met "403 error code: 1010" (gemeten
# 02-09-2026 op de echte API). Zonder deze kop faalt élke aanroep uit dit pakket, dus hij
# hoort in de client en niet in de handleiding.
UA = f"shinobitools-py/{__version__} (+https://shinobitools.com)"


def _post(url: str, velden: dict, bestanden: list[tuple[str, bytes, str]]):
    velden = {"src": SRC, **velden}
    body, soort = _multipart(velden, bestanden)
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": soort, "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            rauw = r.read()
            if "json" in (r.headers.get("Content-Type") or ""):
                return json.loads(rauw.decode())
            return rauw
    except urllib.error.HTTPError as e:
        rauw = e.read().decode(errors="replace")
        try:
            boodschap = json.loads(rauw).get("detail") or json.loads(rauw).get("error") or rauw
        except Exception:                                        # noqa: BLE001
            boodschap = rauw
        raise ShinobiError(e.code, str(boodschap)[:400]) from None


def _get(url: str) -> bytes:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise ShinobiError(e.code, e.read().decode(errors="replace")[:400]) from None


# ── bgninja ────────────────────────────────────────────────────────────────────
def remove_background(image, background: str | None = None) -> bytes:
    """Remove the background from an image. Returns PNG bytes.

    `background` is a hex colour without the '#', e.g. "ffffff". Leave it out for a
    transparent background.
    """
    inhoud, naam = _bytes_van(image)
    return _post(f"{BGNINJA}/api/remove", {"bg": background}, [("file", inhoud, naam)])


# ── passportninja ──────────────────────────────────────────────────────────────
def passport_photo(image, country: str = "eu") -> dict:
    """Turn a portrait into a passport photo. Returns the service's JSON.

    The result includes `head_mm` and `head_range_mm`, so you can check compliance
    yourself. Add `photo_bytes()` on the returned dict via `fetch_result`.
    """
    inhoud, naam = _bytes_van(image)
    return _post(f"{PASSPORTNINJA}/api/photo", {"country": country}, [("file", inhoud, naam)])


def fetch_result(job: dict, key: str = "photo") -> bytes:
    """Download one of the files a passport job produced, e.g. "photo" or "sheet"."""
    pad = job[key]
    return _get(pad if pad.startswith("http") else PASSPORTNINJA + pad)


# ── scanreviver ────────────────────────────────────────────────────────────────
def pdf_merge(*pdfs) -> bytes:
    """Merge two or more PDFs into one. Returns the merged PDF."""
    if len(pdfs) < 2:
        raise ValueError("merging needs at least two PDFs")
    bestanden = []
    for p in pdfs:
        inhoud, naam = _bytes_van(p)
        bestanden.append(("files", inhoud, naam))
    job = _post(f"{SCANREVIVER}/api/pdf-merge", {}, bestanden)
    return _get(f"{SCANREVIVER}/api/pdf-file/{job['id']}")


def pdf_compress(pdf, level: str = "good") -> bytes:
    """Compress a PDF. `level` is the strength the service accepts, "good" by default."""
    inhoud, naam = _bytes_van(pdf)
    job = _post(f"{SCANREVIVER}/api/pdf-compress", {"level": level}, [("file", inhoud, naam)])
    return _get(f"{SCANREVIVER}/api/pdf-file/{job['id']}")


def ocr_text(pdf) -> str:
    """Read the text out of a scanned PDF. Returns the recognised text."""
    inhoud, naam = _bytes_van(pdf)
    return _post(f"{SCANREVIVER}/api/ocr-text", {}, [("file", inhoud, naam)])["text"]


# ── convert ────────────────────────────────────────────────────────────────────
def video_to_gif(video, fps: float = 12.0, width: int = 480) -> bytes:
    """Turn a video into a GIF. Returns GIF bytes."""
    inhoud, naam = _bytes_van(video)
    return _post(f"{CONVERT}/api/gif", {"fps": fps, "breedte": width},
                 [("file", inhoud, naam)])


def video_to_mp3(video) -> bytes:
    """Pull the audio track out of a video. Returns MP3 bytes."""
    inhoud, naam = _bytes_van(video)
    return _post(f"{CONVERT}/api/audio", {"formaat": "mp3"}, [("file", inhoud, naam)])


def vectorize(image, mode: str = "color") -> bytes:
    """Trace a raster image into an SVG. Returns SVG bytes. Best on flat artwork."""
    inhoud, naam = _bytes_van(image)
    return _post(f"{CONVERT}/api/vectorize", {"modus": mode}, [("file", inhoud, naam)])
