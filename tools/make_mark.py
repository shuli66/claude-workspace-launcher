"""从 assets/claude_icon.ico 生成 assets/claude-mark.png。

原图标是暖橙星芒 + 不透明深青灰底。直接贴到奶油色界面上会出现色块，
因此按底色距离做带软边的抠图。Ray 边缘保留阿尔法渐变以免锯齿。
"""

import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "claude_icon.ico"
TARGET = ROOT / "assets" / "claude-mark.png"

SIZE = 256
BACKGROUND = (76, 105, 113)  # 源图标底色的实测值
HARD_CUTOFF = 40             # 距离小于此值视为纯背景
SOFT_CUTOFF = 110            # 介于两者之间做阿尔法渐变
OUTPUT_SIZE = 128


def main():
    image = Image.open(SOURCE)
    image.size = (SIZE, SIZE)
    image = image.convert("RGBA")

    source = image.load()
    result = Image.new("RGBA", image.size, (0, 0, 0, 0))
    target = result.load()

    for y in range(SIZE):
        for x in range(SIZE):
            r, g, b, _ = source[x, y]
            distance = math.sqrt(
                (r - BACKGROUND[0]) ** 2
                + (g - BACKGROUND[1]) ** 2
                + (b - BACKGROUND[2]) ** 2
            )

            if distance < HARD_CUTOFF:
                continue
            if distance < SOFT_CUTOFF:
                alpha = int(255 * (distance - HARD_CUTOFF) / (SOFT_CUTOFF - HARD_CUTOFF))
                target[x, y] = (r, g, b, alpha)
            else:
                target[x, y] = (r, g, b, 255)

    result = result.crop(result.getbbox())
    result = result.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.LANCZOS)
    result.save(TARGET, "PNG", optimize=True)
    print("已写入 %s" % TARGET)


if __name__ == "__main__":
    main()
