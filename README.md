# LiveLingo

中英双语实时字幕工具 — 麦克风拾音 → 实时语音识别 → AI翻译 → 屏幕字幕显示。

基于阿里云百炼 DashScope API，适合线下会议、学术报告、国际交流等场景，为听众实时显示中英双语字幕。

![macOS](https://img.shields.io/badge/macOS-14%2B-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 特性

- **实时语音识别** — 阿里云 Fun-ASR 实时流式识别，中英日多方言，低延迟
- **AI 双向翻译** — 自动检测中/英文，实时翻译为另一种语言
- **悬浮字幕栏** — 深色字幕条，始终置顶，可全屏投射到外接显示器
- **自包含 .app** — 单文件分享，首次运行自动安装依赖
- **麦克风选择** — 自动跳过虚拟音频设备，支持运行中切换
- **设置面板** — 字号、行数、断句速度、API Key 均可在 App 内调整
- **拖拽移动** — 窗口可自由拖拽、调整大小

## 快速开始

### 方式一：直接使用 .app（推荐）

1. 从 [Releases](https://github.com/bidezhu/livelingo/releases) 下载 `LiveLingo.app`
2. 双击运行，首次会自动安装依赖并提示输入 API Key
3. 开始说话，字幕自动显示

### 方式二：源码运行

```bash
git clone https://github.com/bidezhu/livelingo.git
cd livelingo
chmod +x install.sh
./install.sh
```

## API Key

需要阿里云百炼 API Key（用于语音识别和翻译）：

1. 注册 [阿里云百炼](https://bailian.console.aliyun.com)
2. 获取 [API Key](https://bailian.console.aliyun.com/api-key)
3. 首次运行时在设置面板中填入

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Cmd+Q` | 退出 |
| `Cmd+H` | 隐藏/显示字幕 |
| `Cmd+,` | 打开设置 |
| 拖拽标题栏 | 移动窗口 |
| 拖拽边缘 | 调整大小 |

## 底部按钮

| 按钮 | 功能 |
|------|------|
| 全屏 | 铺满屏幕，适合投屏 |
| 适配屏幕 | 回到底部字幕条模式 |
| 麦克风 | 切换音频输入设备 |
| 设置 | 调整字号/行数/API Key |
| 退出 | 关闭应用 |

## 技术架构

```
麦克风 16kHz → sounddevice → DashScope WebSocket → 实时识别结果
                                                        ↓
                                                  DashScope API → 翻译 → 双语字幕
```

| 模块 | 技术 |
|------|------|
| 语音识别 | 阿里云 Fun-ASR Realtime (WebSocket 流式) |
| 翻译 | 阿里云 Qwen-Plus (DashScope API) |
| 音频采集 | sounddevice |
| 字幕UI | Python Tkinter |

## 项目结构

```
livelingo/
├── LiveLingo.app       # macOS 应用（自包含，可单独分享）
├── launcher.py         # App 启动器（首次安装、环境检查）
├── main.py             # 主程序入口
├── asr_engine.py       # DashScope 实时语音识别
├── translator.py       # DashScope 翻译模块
├── audio_capture.py    # 麦克风音频采集
├── subtitle_ui.py      # 字幕悬浮窗口
├── device_selector.py  # 麦克风选择对话框
├── settings_panel.py   # 设置面板
├── config.py           # 配置管理
├── build_app.py        # 构建 .app 脚本
├── install.sh          # 一键安装脚本
├── run.sh              # 终端启动脚本
└── requirements.txt    # Python 依赖
```

## 构建 .app

```bash
python3 build_app.py
# 输出: LiveLingo.app (196KB, 自包含)
```

分享给其他 Mac 用户只需发送 `LiveLingo.app` 这一个文件。

## License

MIT License
