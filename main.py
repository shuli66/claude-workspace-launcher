"""Claude Launcher 启动入口。

单独一层薄入口是为了让 PyInstaller 有明确的入口脚本，同时保持包内可测试。
"""

from claude_launcher.app import main

if __name__ == "__main__":
    main()
