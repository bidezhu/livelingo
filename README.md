# LiveLingo

中英双语实时字幕工具：麦克风 / 系统音频 → Qwen 实时同传模型 → 全屏双语字幕。

LiveLingo is a bilingual real-time captioning app for Chinese-English meetings, academic talks, and public-health discussions. It captures microphone or system audio, streams it to Qwen LiveTranslate, and displays clean bilingual subtitles for audiences.

![macOS](https://img.shields.io/badge/macOS-14%2B-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-green)
![Release](https://img.shields.io/github/v/release/bidezhu/livelingo)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 核心特性 / Key Features

- **实时同传模型 / Realtime LiveTranslate**<br>
  基于 `qwen3.5-livetranslate-flash-realtime` WebSocket 流式音频翻译。<br>
  Powered by `qwen3.5-livetranslate-flash-realtime` over a streaming WebSocket connection.

- **流式字幕草稿 / Streaming Subtitle Drafts**<br>
  转写和翻译增量会立即显示，分段完成后再固化为正式字幕。<br>
  Transcription and translation deltas appear immediately, then become stable caption segments once finalized.

- **智能中英互译 / Smart Chinese-English Translation**<br>
  支持智能双向模式，也支持“中文发言为主”和“英文发言为主”单向模式。<br>
  Supports automatic bidirectional mode, plus Chinese-primary and English-primary modes for more stable single-language talks.

- **学术演讲优化 / Academic Talk Optimization**<br>
  默认更适配学术报告语速，过滤常见口气词，并让字幕更靠视觉中心。<br>
  Tuned for lecture-style pacing, common filler-word cleanup, and visually centered subtitles.

- **公共卫生词库 / Public-Health Vocabulary Boost**<br>
  默认强化流行病学、卫生政策、儿童肥胖、含糖饮料税、卫生体系、WHO、UNICEF、ASEAN 等术语。<br>
  Includes built-in terminology for epidemiology, health policy, childhood obesity, SSB tax, health systems, WHO, UNICEF, ASEAN, and related topics.

- **麦克风、系统音频、混合输入 / Microphone, System Audio, Mixed Input**<br>
  支持麦克风、BlackHole / Loopback 类虚拟系统音频输入，以及麦克风 + 系统音频混合模式。<br>
  Supports microphone input, virtual system-audio devices such as BlackHole / Loopback, and mixed microphone + system audio capture.

- **全屏会议字幕 / Full-Screen Meeting Captions**<br>
  深色字幕条始终置顶，可用于投屏、外接屏和会议室显示。<br>
  Always-on-top dark caption window designed for projection, external displays, and meeting-room use.

- **设置面板 / Settings Panel**<br>
  可调整 API Key、发言语言模式、音频来源、字号、字幕段落、垂直位置、热词和分段参数。<br>
  Configure API key, language mode, audio source, font sizes, caption segments, vertical position, hot words, and segmentation behavior.

## 快速开始 / Quick Start

### 方式一：下载 macOS App / Option 1: Download the macOS App

1. 打开 [Releases](https://github.com/bidezhu/livelingo/releases) 页面。<br>
   Open the [Releases](https://github.com/bidezhu/livelingo/releases) page.
2. 下载 `LiveLingo-v1.2.0-macOS.zip`。<br>
   Download `LiveLingo-v1.2.0-macOS.zip`.
3. 解压后双击 `LiveLingo.app`。首次运行会安装依赖并提示填写 API Key。<br>
   Unzip it and double-click `LiveLingo.app`. On first launch, it installs dependencies and asks for your API key.
4. 选择音频来源，开始说话或播放会议音频。<br>
   Choose an audio source, then start speaking or playing meeting audio.

### 方式二：源码运行 / Option 2: Run from Source

```bash
git clone https://github.com/bidezhu/livelingo.git
cd livelingo
chmod +x install.sh
./install.sh
```

## API Key / API Key

LiveLingo 需要阿里云百炼 DashScope API Key，用于实时语音识别与翻译。<br>
LiveLingo requires an Alibaba Cloud Bailian / DashScope API key for realtime speech recognition and translation.

1. 注册或登录 [阿里云百炼](https://bailian.console.aliyun.com)。<br>
   Register or sign in to [Alibaba Cloud Bailian](https://bailian.console.aliyun.com).
2. 在控制台获取 API Key。<br>
   Create or copy your API key from the console.
3. 在 LiveLingo 设置面板中填入。<br>
   Paste it into the LiveLingo settings panel.

安全说明：仓库和 release 包不会内置默认 API Key。<br>
Security note: the repository and release package do not ship with a default API key.

## 使用建议 / Usage Tips

### 英文会议 / English Talks

如果整场主要是英文发言，请在“设置 → API → 发言语言”中选择“英文发言为主”。<br>
If the talk is mainly in English, choose “English-primary” in “Settings → API → Speaking Language”.

这样只开启英译中实时会话，英文识别和翻译更顺滑，也更不容易触发服务端限流。<br>
This starts only the English-to-Chinese realtime session, improving smoothness and reducing rate-limit pressure.

### 中文会议 / Chinese Talks

如果整场主要是中文发言，请选择“中文发言为主”。<br>
If the talk is mainly in Chinese, choose “Chinese-primary”.

### 中英混合讨论 / Mixed Chinese-English Discussion

如果发言人频繁中英切换，请选择“智能中英互译”。<br>
For frequent language switching, choose “Smart bidirectional translation”.

### 系统音频 / System Audio

macOS 不提供原生 loopback 录音。若要捕获会议软件或视频播放声音，建议安装并配置 BlackHole、Loopback 或类似虚拟音频设备。<br>
macOS does not provide native loopback recording. To capture meeting-app or video playback audio, install and configure BlackHole, Loopback, or a similar virtual audio device.

## 快捷键 / Shortcuts

| 快捷键 / Shortcut | 功能 / Action |
|---|---|
| `Cmd+Q` | 退出 / Quit |
| `Cmd+H` | 隐藏或显示字幕 / Hide or show captions |
| `Cmd+,` | 打开设置 / Open settings |
| 拖拽标题栏 / Drag title area | 移动窗口 / Move window |
| 拖拽边缘 / Drag window edge | 调整大小 / Resize window |

## 底部按钮 / Bottom Controls

| 按钮 / Button | 功能 / Action |
|---|---|
| 全屏 / Full Screen | 铺满屏幕，适合投屏 / Fill the screen for projection |
| 适配 / Fit | 回到底部字幕条模式 / Return to bottom caption-bar mode |
| 音频来源 / Audio Source | 切换麦克风、系统音频或混合输入 / Switch microphone, system audio, or mixed input |
| 设置 / Settings | 调整 API、字幕、分段、热词和显示参数 / Configure API, captions, segmentation, hot words, and display |
| 退出 / Quit | 关闭应用 / Close the app |

## 技术架构 / Architecture

```text
Microphone / System Audio 16 kHz
        ↓
sounddevice / soundcard capture
        ↓
audio fan-out
        ├─ zh→en LiveTranslate session
        └─ en→zh LiveTranslate session
        ↓
streaming drafts + finalized bilingual subtitle segments
```

| 模块 / Module | 技术 / Technology |
|---|---|
| 实时同传 / Realtime translation | Alibaba Cloud Qwen LiveTranslate Realtime WebSocket |
| 源文转写 / Source transcription | `qwen3-asr-flash-realtime` |
| 双向翻译 / Bidirectional translation | `qwen3.5-livetranslate-flash-realtime` |
| 音频采集 / Audio capture | `sounddevice`, `soundcard` |
| 字幕 UI / Caption UI | Python Tkinter |
| 打包 / Packaging | Self-contained macOS `.app` launcher |

## 项目结构 / Project Structure

```text
livelingo/
├── LiveLingo.app              # macOS app bundle / macOS 应用包
├── launcher.py                # app launcher / 应用启动器
├── main.py                    # main entrypoint / 主程序入口
├── live_translate_engine.py   # Qwen realtime translation engine / 实时同传引擎
├── system_audio_capture.py    # system + mixed audio capture / 系统音频与混合采集
├── subtitle_ui.py             # subtitle window / 字幕窗口
├── device_selector.py         # audio source selector / 音频来源选择器
├── settings_panel.py          # settings panel / 设置面板
├── config.py                  # defaults and hot words / 默认配置与热词
├── build_app.py               # build script / .app 构建脚本
├── test_live_translate_engine.py
├── install.sh
├── run.sh
└── requirements.txt
```

## 构建 App / Build the App

```bash
python3 build_app.py
```

输出文件为 `LiveLingo.app`。<br>
The output is `LiveLingo.app`.

如需发布，建议压缩为 zip 后上传到 GitHub Releases。<br>
For distribution, zip the app bundle and upload it to GitHub Releases.

## 测试 / Tests

```bash
python3 -m unittest -v test_live_translate_engine.py
python3 -m py_compile config.py build_app.py launcher.py main.py live_translate_engine.py subtitle_ui.py settings_panel.py system_audio_capture.py device_selector.py
```

## License / 许可证

MIT License
