"""Convert the supplied PNG to Windows ICO frames without altering the artwork."""
from pathlib import Path
import struct

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QImage

ROOT = Path(__file__).resolve().parents[1]
source = QImage(str(ROOT / 'desktop/assets/youdu.png'))
if source.isNull() or source.width() != source.height():
    raise ValueError('Expected a square source PNG')
frames = []
for size in (16, 24, 32, 48, 64, 128, 256):
    picture = source.scaled(
        size, size, Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    if size == 256:
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not picture.save(buffer, 'PNG'):
            raise ValueError('PNG encoding failed')
        buffer.close()
        payload = bytes(data)
    else:
        # Windows DIB stores BGRA rows from bottom to top.
        picture = picture.convertToFormat(QImage.Format.Format_ARGB32)
        raw = bytes(picture.constBits())
        stride = picture.bytesPerLine()
        pixels = b''.join(
            raw[y * stride:y * stride + size * 4] for y in reversed(range(size))
        )
        mask_stride = ((size + 31) // 32) * 4
        mask = bytearray(mask_stride * size)
        for row in range(size):
            for col in range(size):
                if pixels[(row * size + col) * 4 + 3] == 0:
                    mask[row * mask_stride + col // 8] |= 0x80 >> (col % 8)
        header = struct.pack(
            '<IiiHHIIiiII', 40, size, size * 2, 1, 32, 0,
            len(pixels) + len(mask), 0, 0, 0, 0,
        )
        payload = header + pixels + mask
    frames.append((size, payload))
offset = 6 + 16 * len(frames)
directory = []
for size, payload in frames:
    directory.append(struct.pack(
        '<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(payload), offset,
    ))
    offset += len(payload)
target = ROOT / 'desktop/assets/youdu-app.ico'
target.write_bytes(
    struct.pack('<HHH', 0, 1, len(frames))
    + b''.join(directory) + b''.join(p for _, p in frames)
)
print('Created ICO frames: 16, 24, 32, 48, 64, 128, 256')
