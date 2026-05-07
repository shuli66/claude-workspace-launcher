import requests
from PIL import Image
from io import BytesIO
import os

def download_claude_icon():
    """下载 Claude 官方 logo 并转换为 ICO 格式"""

    # Claude logo URL (使用 Anthropic 官方资源)
    logo_url = "https://www.anthropic.com/images/icons/claude-app-icon.png"

    try:
        print("正在下载 Claude logo...")
        response = requests.get(logo_url, timeout=10)
        response.raise_for_status()

        # 打开图片
        img = Image.open(BytesIO(response.content))

        # 转换为 RGBA 模式
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # 保存为 ICO 文件（多尺寸）
        icon_path = os.path.join(os.path.dirname(__file__), "claude_icon.ico")
        img.save(icon_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

        print(f"✓ 图标已保存到: {icon_path}")
        return icon_path

    except Exception as e:
        print(f"✗ 下载失败: {e}")
        print("将使用默认图标")
        return None

if __name__ == "__main__":
    download_claude_icon()
