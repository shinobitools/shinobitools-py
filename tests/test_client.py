"""Eén controle die faalt zodra de multipart-opbouw stukgaat.

Dat is het enige echt niet-triviale stuk in dit pakket: de rest is een URL en een
JSON-sleutel. Draait zonder net.

    python3 tests/test_client.py          # offline, altijd
    LIVE=1 python3 tests/test_client.py   # ook één echte aanroep naar de API
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shinobitools import SRC, _bytes_van, _multipart, remove_background  # noqa: E402


def test_multipart():
    body, soort = _multipart({"src": SRC, "bg": "ffffff", "leeg": None},
                             [("file", b"\x89PNG-nep", "kat.png")])
    tekst = body.decode("latin-1")

    grens = soort.split("boundary=")[1]
    assert soort.startswith("multipart/form-data; "), soort
    # de scheiding moet echt in de body staan, en de body moet erop eindigen
    assert tekst.startswith(f"--{grens}\r\n"), "body begint niet met de scheiding"
    assert tekst.endswith(f"--{grens}--\r\n"), "body sluit niet af met de slot-scheiding"
    # gewone velden
    assert 'name="src"' in tekst and SRC in tekst
    assert 'name="bg"' in tekst and "ffffff" in tekst
    # None-velden horen NIET mee te gaan: anders stuurt de client de tekst "None"
    assert 'name="leeg"' not in tekst, "een leeg veld werd toch meegestuurd"
    # bestand met naam, type en de rauwe bytes
    assert 'name="file"; filename="kat.png"' in tekst
    assert "Content-Type: image/png" in tekst
    assert b"\x89PNG-nep" in body, "de bestandsinhoud staat niet in de body"
    print("  multipart ok")


def test_bytes_van():
    assert _bytes_van(b"abc") == (b"abc", "upload")
    pad = os.path.join(os.path.dirname(__file__), "_proef.txt")
    with open(pad, "wb") as f:
        f.write(b"hallo")
    try:
        assert _bytes_van(pad) == (b"hallo", "_proef.txt")
        with open(pad, "rb") as f:
            assert _bytes_van(f) == (b"hallo", "_proef.txt")
    finally:
        os.remove(pad)
    print("  bytes_van ok")


def test_live():
    """Alleen met LIVE=1: één echte aanroep, zodat 'het werkt' geen aanname is."""
    import io
    import struct
    import zlib

    def mini_png() -> bytes:                       # 2x2 rood, zonder Pillow
        def blok(soort, data):
            return (struct.pack(">I", len(data)) + soort + data
                    + struct.pack(">I", zlib.crc32(soort + data)))
        rauw = b"".join(b"\x00" + b"\xff\x00\x00" * 2 for _ in range(2))
        return (b"\x89PNG\r\n\x1a\n"
                + blok(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
                + blok(b"IDAT", zlib.compress(rauw))
                + blok(b"IEND", b""))

    uit = remove_background(mini_png())
    assert uit[:8] == b"\x89PNG\r\n\x1a\n", "de service gaf geen PNG terug"
    print(f"  live ok — {len(uit)} bytes PNG terug")
    _ = io.BytesIO


if __name__ == "__main__":
    test_multipart()
    test_bytes_van()
    if os.environ.get("LIVE"):
        test_live()
    else:
        print("  live overgeslagen (zet LIVE=1)")
    print("alles ok")
