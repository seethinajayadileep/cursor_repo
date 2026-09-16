#!/usr/bin/env python3
"""Write simple maskable PNG icons (stdlib only)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "web" / "icons"


def write_png(path: Path, rows: list[list[tuple[int, int, int, int]]]) -> None:
    height = len(rows)
    width = len(rows[0])

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw = b"".join(b"\x00" + bytes(ch for px in row for ch in px) for row in rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    )


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def icon(size: int) -> list[list[tuple[int, int, int, int]]]:
    rows: list[list[tuple[int, int, int, int]]] = []
    cx = cy = size / 2
    for y in range(size):
        row: list[tuple[int, int, int, int]] = []
        for x in range(size):
            nx = (x + 0.5) / size
            ny = (y + 0.5) / size
            # rounded square safe zone
            inset = 0.08
            rx = min(nx - inset, 1 - inset - nx)
            ry = min(ny - inset, 1 - inset - ny)
            r = min(rx, ry)
            if r < 0:
                row.append((0, 0, 0, 0))
                continue
            corner = 0.16
            in_round = r > 0 or (nx > inset + corner and nx < 1 - inset - corner) or (
                ny > inset + corner and ny < 1 - inset - corner
            )
            dx = 0.0
            dy = 0.0
            if nx < inset + corner:
                dx = (inset + corner) - nx
            elif nx > 1 - inset - corner:
                dx = nx - (1 - inset - corner)
            if ny < inset + corner:
                dy = (inset + corner) - ny
            elif ny > 1 - inset - corner:
                dy = ny - (1 - inset - corner)
            if dx and dy and (dx * dx + dy * dy) > corner * corner:
                row.append((0, 0, 0, 0))
                continue
            _ = in_round
            bg = (26, 22, 18, 255)
            # amber fill toward top-right
            t = max(0.0, 1.0 - ((nx - 0.35) ** 2 + (ny - 0.3) ** 2) * 2.2)
            col = (
                lerp(bg[0], 245, t * 0.35),
                lerp(bg[1], 165, t * 0.35),
                lerp(bg[2], 36, t * 0.35),
                255,
            )
            # pocket body
            pocket = 0.28 < nx < 0.72 and 0.34 < ny < 0.78
            flap = abs(ny - 0.38) < 0.035 and 0.30 < nx < 0.70
            # send chevron
            chev = False
            px = nx - 0.5
            py = ny - 0.52
            if abs(px) < 0.16 and -0.14 < py < 0.12:
                chev = abs(px) < 0.045 and py < 0.08
                chev = chev or (py > -0.02 and abs(px) + (py + 0.02) * 1.1 < 0.16 and py < 0.12)
            if pocket:
                col = (245, 165, 36, 255) if not chev else (26, 22, 18, 255)
            if flap:
                col = (255, 214, 140, 255)
            row.append(col)
        rows.append(row)
        _ = (cx, cy)
    return rows


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        write_png(ROOT / f"icon-{size}.png", icon(size))
        print("wrote", ROOT / f"icon-{size}.png")


if __name__ == "__main__":
    main()
