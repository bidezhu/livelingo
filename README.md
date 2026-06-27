# LiveLingo

本地离线中英双语实时字幕工具 — 麦克风拾音 → 实时语音识别 → AI翻译 → 屏幕字幕显示。

纯本地运行，无需联网，适合线下会议、学术报告等场景为专家实时显示中英双语字幕。

## 特性

- **实时语音识别** — 基于 FunASR Paraformer 流式模型，中文识别准确率高
- **AI 双向翻译** — 自动检测中/英文，实时翻译为另一种语言
- **标点恢复** — 集成 ct-punc 模型，最终结果自动加标点
- **悬浮字幕栏** — 深色底部字幕条，始终置顶，不干扰演示
- **麦克风选择** — 支持切换任意音频输入设备
- **设置面板** — 字号、行数、断句速度等均可在 App 内调整
- **纯本地离线** — 所有模型本地运行，无需外网

## 硬件要求

| 配置 | 最低要求 | 推荐 |
|------|----------|------|
| 芯片 | Apple Silicon (M1+) | M4 Pro |
| 内存 | 8GB | 16GB+ |
| 磁盘 | 10GB | - |
| 系统 | macOS 14 Sonoma+ | - |

## 快速开始

### 1. 安装

```bash
git clone https://github.com/bidezhu/livelingo.git
cd livelingo
chmod +x install.sh
./install.sh
```

安装向导会自动：
- 检查 Python 环境
- 创建虚拟环境并安装依赖
- 引导输入百炼 API Key
- 生成 LiveLingo.app

### 2. 运行

```bash
# 双击 LiveLingo.app
# 或终端运行 ./run.sh
```

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Cmd+Q` | 退出 |
| `Cmd+↑/↓` | 上下移动字幕栏 |
| `Cmd+H` | 隐藏/显示字幕 |
| `Cmd+,` | 打开设置 |

## 技术架构

```
麦克风 16kHz → sounddevice → FunASR 流式识别 → 中间结果(灰) / 最终结果(白)
                                                        ↓
                                                  Ollama(Qwen3.5) → 英文/中文字幕
```

| 模块 | 技术 |
|------|------|
| 语音识别 | FunASR Paraformer-zh-streaming |
| 标点恢复 | FunASR ct-punc |
| 翻译 | Ollama + Qwen3.5:9b (Metal GPU加速) |
| 音频采集 | sounddevice |
| 字幕UI | Python Tkinter |

## 项目结构

```
livelingo/
├── launcher.py         # App 启动器（环境检查）
├── main.py             # 主程序入口
├── asr_engine.py       # FunASR 流式语音识别
├── translator.py       # Ollama 翻译模块
├── audio_capture.py    # 麦克风音频采集
├── subtitle_ui.py      # 字幕悬浮窗口
├── device_selector.py  # 麦克风选择对话框
├── settings_panel.py   # 设置面板
├── config.py           # 配置管理
├── setup.sh            # 环境安装脚本
├── run.sh              # 启动脚本
├── build_app.sh        # 打包 .app 脚本
└── requirements.txt    # Python 依赖
```

## 构建 .app

```bash
./build_app.sh
# 输出: dist/LiveSubtitle.app (~700MB)
```

## License

MIT License
