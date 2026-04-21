# 声音克隆 - 安装与配置指南

## 环境要求

- Python >= 3.9
- ffmpeg（音频处理）
- yt-dlp（从网络下载音频）
- GPU（可选，Qwen3-TTS 本地克隆需要）

## 克隆引擎选择

| 方案 | 条件 | 安装 | 特点 |
|------|------|------|------|
| **Qwen3-TTS（推荐）** | NVIDIA GPU | `pip install qwen-tts` | 本地推理，3秒音频克隆，免费无限制 |
| **Fish Audio** | 无需GPU | 注册获取 API Key | 云端，免费额度每天1万字 |

脚本会自动检测：有GPU + qwen-tts → 本地克隆，否则 → Fish Audio 云端。

## 安装步骤

### 1. 安装系统依赖

```bash
# macOS
brew install ffmpeg

# CentOS / Alibaba Cloud Linux
yum install -y ffmpeg

# Ubuntu / Debian
apt install -y ffmpeg
```

### 2. 安装 Python 依赖

```bash
pip install yt-dlp httpx
```

> Hermes Agent 用户：
> ```bash
> /home/admin/.hermes/hermes-agent/venv/bin/python3 -m pip install yt-dlp httpx
> ```

### 3. 安装 Qwen3-TTS（推荐，需要 GPU）

如果服务器有 NVIDIA GPU，安装 Qwen3-TTS 实现本地克隆：

```bash
pip install -U qwen-tts

# 可选：安装 FlashAttention-2 减少显存占用
pip install -U flash-attn --no-build-isolation
```

> 模型在首次运行时自动下载（0.6B 模型约 1.2GB）。
> 也可手动下载：
> ```bash
> # 从 ModelScope（国内快）
> pip install modelscope
> modelscope download Qwen/Qwen3-TTS-0.6B-CustomVoice
>
> # 或从 HuggingFace
> huggingface-cli download Qwen/Qwen3-TTS-0.6B-CustomVoice
> ```

### 4. 配置 Fish Audio（备选/无GPU时使用）

访问 https://fish.audio 注册账号，获取 API Key（免费额度：每天 10,000 字）。

```bash
export FISH_AUDIO_API_KEY="你的api_key"
```

> Hermes Agent 用户可写入 `~/.hermes/.env`：
> ```bash
> echo 'FISH_AUDIO_API_KEY=你的api_key' >> ~/.hermes/.env
> ```

### 5. 复制 skill 到 agent 的 skills 目录

```bash
git clone https://github.com/zhihong-swb/hermes-tts.git

# Hermes Agent
cp -r hermes-tts/voice-clone ~/.hermes/skills/

# Claude Code
cp -r hermes-tts/voice-clone ~/.claude/skills/

# Qoder
cp -r hermes-tts/voice-clone ~/.qoder/skills/
```

### 6. 验证

```bash
# 测试搜索（通过公开搜索引擎，无需登录）
python scripts/search_audio.py --name "雷军" --max-results 2

# 测试音频处理
python scripts/prepare_audio.py --input test.mp3 --duration 10

# 测试克隆引擎检测
python scripts/clone_voice.py --list
```

---

## 音频质量建议

克隆效果取决于参考音频质量：

| 项目 | 建议 |
|------|------|
| 时长 | Qwen3-TTS 最少3秒，推荐10-30秒 |
| 格式 | WAV 最佳，MP3 也可 |
| 采样率 | 16kHz 以上 |
| 内容 | 纯人声，无背景音乐/噪声 |
| 语速 | 正常语速，吐字清晰 |

## 常见问题

### Q: 搜索不到某人的音频

- 脚本默认通过搜索引擎查找，无需登录
- 尝试不同关键词：`--keyword "采访"` 或 `--keyword "TED"`
- 也可直接提供视频链接：`--url "https://..."`

### Q: 如何检查服务器是否有 GPU

```bash
nvidia-smi
```
如果有输出说明有 GPU，可以使用 Qwen3-TTS 本地克隆。

### Q: Qwen3-TTS 下载太慢

使用 ModelScope 国内镜像：
```bash
pip install modelscope
modelscope download Qwen/Qwen3-TTS-0.6B-CustomVoice
```

### Q: 克隆效果不好

- 确保音频是纯人声，用 `--denoise` 降噪
- 多提供几段音频样本（`--audio a.wav b.wav c.wav`）
- 裁剪掉开头结尾的杂音
- Qwen3-TTS 效果一般优于 Fish Audio 免费版

### Q: Fish Audio 免费额度用完了

- 免费额度每天重置（10,000 字/天）
- 模型创建不计入额度，仅合成时消耗
- 推荐切换到 Qwen3-TTS 本地克隆（无限制）
