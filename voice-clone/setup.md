# 声音克隆 - 安装与配置指南

## 环境要求

- Python >= 3.9
- ffmpeg（音频处理）
- yt-dlp（从网络下载音频）
- 网络连接

## 安装步骤

### 1. 安装系统依赖

```bash
# macOS
brew install ffmpeg yt-dlp

# CentOS / Alibaba Cloud Linux
yum install -y ffmpeg
pip install yt-dlp

# Ubuntu / Debian
apt install -y ffmpeg
pip install yt-dlp
```

### 2. 安装 Python 依赖

```bash
pip install httpx yt-dlp
```

> Hermes Agent 用户：
> ```bash
> /home/admin/.hermes/hermes-agent/venv/bin/python3 -m pip install httpx yt-dlp
> ```

### 3. 配置 Fish Audio API Key

访问 https://fish.audio 注册账号，获取 API Key（免费额度：每天 10,000 字）。

```bash
export FISH_AUDIO_API_KEY="你的api_key"
```

> Hermes Agent 用户可写入 `~/.hermes/.env`：
> ```bash
> echo 'FISH_AUDIO_API_KEY=你的api_key' >> ~/.hermes/.env
> ```

### 4. 复制 skill 到 agent 的 skills 目录

```bash
git clone https://github.com/zhihong-swb/hermes-tts.git

# Hermes Agent
cp -r hermes-tts/voice-clone ~/.hermes/skills/

# Claude Code
cp -r hermes-tts/voice-clone ~/.claude/skills/

# Qoder
cp -r hermes-tts/voice-clone ~/.qoder/skills/
```

### 5. 验证

```bash
# 测试搜索
python scripts/search_audio.py --name "雷军" --max-results 2

# 测试音频处理
python scripts/prepare_audio.py --input test.mp3 --duration 10

# 测试列出模型
python scripts/clone_voice.py --list
```

---

## 音频质量建议

克隆效果取决于参考音频质量：

| 项目 | 建议 |
|------|------|
| 时长 | 10-30 秒（太短效果差，太长无意义） |
| 格式 | WAV 最佳，MP3 也可 |
| 采样率 | 16kHz 以上 |
| 内容 | 纯人声，无背景音乐/噪声 |
| 语速 | 正常语速，吐字清晰 |

## 常见问题

### Q: 搜索不到某人的音频

- 尝试不同关键词：`--keyword "采访"` 或 `--keyword "TED"`
- 英文人名用英文搜索
- 部分人物可能没有公开音频

### Q: 克隆效果不好

- 确保音频是纯人声，用 `--denoise` 降噪
- 多提供几段音频样本（`--audio a.wav b.wav c.wav`）
- 裁剪掉开头结尾的杂音

### Q: Fish Audio 免费额度用完了

- 免费额度每天重置（10,000 字/天）
- 模型创建不计入额度，仅合成时消耗
- 已创建的模型可无限使用
