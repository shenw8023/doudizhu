[app]

# App 信息
title = 斗地主
package.name = doudizhu
package.domain = com.doudizhu

# 项目根目录作为源码目录
source.dir = .
source.main = android/main.py

# 包含的文件
source.include_exts = py,json
source.include_patterns = src/*.py,src/**/*.py,android/*.py

version = 1.0.0

# 依赖
requirements = python3,kivy

# 全屏
fullscreen = 1

# 竖屏
orientation = portrait

# Android 配置
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a

# 日志
log_level = 2

[buildozer]
warn_on_root = 0
