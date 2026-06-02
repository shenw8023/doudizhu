# 斗地主 Android App

## 快速构建（推荐）

在 Linux 或 macOS 开发机上：

```bash
cd /ubuntu/doudizhu
chmod +x build_apk.sh
./build_apk.sh
```

首次构建约 30-60 分钟（需下载 Android SDK/NDK）。
构建完成后 APK 在 `bin/` 目录下。

## 手动构建步骤

### 环境要求

- Python 3.9+
- Java JDK 17
- Linux 或 macOS（Windows 需要 WSL）

### 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install kivy buildozer cython
```

### 构建 APK

```bash
# 设置 Java 路径（如果不在 PATH 中）
export JAVA_HOME=/path/to/jdk17
export PATH=$JAVA_HOME/bin:$PATH

# 构建 debug 版本
buildozer android debug

# 构建 release 版本（需要签名）
buildozer android release
```

### 安装到手机

```bash
# USB 安装
adb install bin/doudizhu-1.0.0-debug.apk

# 或直接发送 APK 文件到手机安装
```

## 项目结构

```
doudizhu/
├── buildozer.spec          # Android 构建配置
├── build_apk.sh            # 一键构建脚本
├── android/
│   └── main.py             # Kivy UI 入口（Android 版）
├── src/
│   ├── engine/             # 游戏引擎（复用）
│   └── ai/                 # AI 引擎（复用）
└── main.py                 # TUI 入口（桌面版）
```

## 自定义

- 修改 `buildozer.spec` 中的 `title`、`package.name`、`package.domain`
- 修改 `android/main.py` 中的 `MCTSAI(num_simulations=50)` 调整 AI 强度
- 修改颜色常量自定义 UI 配色

## 常见问题

**Q: 构建失败 "Java not found"**
A: 安装 JDK 17 并设置 JAVA_HOME 环境变量。

**Q: 构建失败 "unzip not found"**
A: 安装 unzip: `sudo apt install unzip`

**Q: 构建很慢**
A: 首次构建需要下载 Android SDK/NDK (~2GB)，后续构建会快很多。

**Q: 手机提示"未知来源"**
A: 在手机设置中允许安装未知来源应用。
