#!/bin/bash
# ============================================================
# 斗地主 Android APK 一键构建脚本
# 
# 注意：需要在 x86_64 Linux 或 macOS 上运行
# ARM64 Linux (如 OrbStack) 不支持，因为 Android SDK 工具只有 x86_64 二进制
# 推荐方案：推送到 GitHub，用 GitHub Actions 自动构建（免费）
# ============================================================
set -e

echo "=== 斗地主 Android APK 构建脚本 ==="
echo ""

# 检查架构
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    echo "⚠️  当前是 ARM64 架构，Android SDK 工具不支持。"
    echo ""
    echo "推荐方案：推送到 GitHub，用 Actions 自动构建："
    echo "  1. git remote add origin https://github.com/你的用户名/doudizhu.git"
    echo "  2. git push -u origin master"
    echo "  3. 在 GitHub 仓库 → Actions 页面查看构建进度"
    echo "  4. 构建完成后在 Artifacts 下载 APK"
    echo ""
    echo "或在 x86_64 Linux/macOS 机器上重新运行此脚本。"
    exit 1
fi

# 1. 检查并安装系统依赖
echo "[1/6] 检查系统依赖..."
if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq build-essential git python3 python3-pip python3-venv \
        unzip zip openjdk-17-jdk autoconf libtool pkg-config \
        zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 \
        cmake libffi-dev libssl-dev 2>/dev/null
elif command -v brew &>/dev/null; then
    brew install java17
fi

# 2. 检查 Java
echo "[2/6] 检查 Java..."
if ! command -v javac &>/dev/null; then
    echo "错误: 需要 Java JDK 17。请安装后重试。"
    exit 1
fi
javac -version

# 3. 创建虚拟环境
echo "[3/6] 创建 Python 虚拟环境..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# 4. 安装依赖
echo "[4/6] 安装 Python 依赖..."
pip install --upgrade pip -q
pip install kivy buildozer cython -q

# 5. 构建 APK
echo "[5/6] 开始构建 APK（首次构建约 30-60 分钟）..."
buildozer android debug

# 6. 完成
echo ""
echo "[6/6] 构建完成！"
APK=$(find bin -name "*.apk" | head -1)
if [ -n "$APK" ]; then
    echo "APK 文件: $SCRIPT_DIR/$APK"
    echo ""
    echo "发送给对方：直接传 APK 文件，手机上安装即可"
else
    echo "未找到 APK 文件，请检查构建日志"
fi
