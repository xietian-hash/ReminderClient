from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRectF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = PROJECT_ROOT / 'assets' / 'app_icon.svg'
ICO_PATH = PROJECT_ROOT / 'assets' / 'app_icon.ico'
PNG_PATH = PROJECT_ROOT / 'assets' / 'app_icon.png'
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def render_icon(size: int, renderer: QSvgRenderer) -> bytes:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, 'PNG', quality=100)
    buffer.close()
    return bytes(byte_array)


def write_ico(png_frames: dict[int, bytes], output_path: Path) -> None:
    count = len(png_frames)
    header = struct.pack('<HHH', 0, 1, count)
    entries = bytearray()
    data = bytearray()
    offset = 6 + (16 * count)

    for size, png_data in png_frames.items():
        width = 0 if size >= 256 else size
        height = 0 if size >= 256 else size
        entries.extend(
            struct.pack(
                '<BBBBHHII',
                width,
                height,
                0,
                0,
                1,
                32,
                len(png_data),
                offset,
            )
        )
        data.extend(png_data)
        offset += len(png_data)

    output_path.write_bytes(header + entries + data)


def main() -> None:
    renderer = QSvgRenderer(str(SVG_PATH))
    if not renderer.isValid():
        raise SystemExit(f'Failed to load SVG icon: {SVG_PATH}')

    png_frames = {size: render_icon(size, renderer) for size in ICON_SIZES}
    write_ico(png_frames, ICO_PATH)
    PNG_PATH.write_bytes(png_frames[256])
    print(f'Generated icon: {ICO_PATH}')
    print(f'Sizes: {list(png_frames)}')


if __name__ == '__main__':
    main()
