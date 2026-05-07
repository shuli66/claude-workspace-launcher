from PIL import Image, ImageDraw
import os

def create_claude_icon():
    """创建 Claude 风格的图标"""

    # 创建一个 256x256 的图像
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Claude 橙色
    claude_orange = (217, 119, 6)

    # 绘制圆角矩形背景
    margin = 20
    draw.rounded_rectangle(
        [(margin, margin), (size - margin, size - margin)],
        radius=40,
        fill=claude_orange
    )

    # 绘制闪电符号（简化版）
    lightning_color = (255, 255, 255)

    # 闪电路径
    points = [
        (size * 0.55, size * 0.25),  # 顶部
        (size * 0.45, size * 0.5),   # 中间左
        (size * 0.52, size * 0.5),   # 中间右
        (size * 0.42, size * 0.75),  # 底部
        (size * 0.48, size * 0.55),  # 中间下左
        (size * 0.45, size * 0.55),  # 中间下右
    ]

    draw.polygon(points, fill=lightning_color)

    # 保存为 ICO 文件
    icon_path = os.path.join(os.path.dirname(__file__), "claude_icon.ico")
    img.save(icon_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    print(f"Icon created: {icon_path}")
    return icon_path

if __name__ == "__main__":
    create_claude_icon()
