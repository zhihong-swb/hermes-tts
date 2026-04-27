# 声音克隆 - 安装与配置指南

## 环境要求

- Python >= 3.9
- ffmpeg（音频处理）
- yt-dlp（从网络下载音频）
- NVIDIA GPU 或 Apple Silicon（Qwen3-TTS 本地克隆）

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
pip install yt-dlp
```

> Hermes Agent 用户：
> ```bash
> /home/admin/.hermes/hermes-agent/venv/bin/python3 -m pip install yt-dlp
> ```

### 3. 安装 Qwen3-TTS

#### Linux 服务器（NVIDIA GPU）

```bash
pip install -U qwen-tts

# 可选：安装 FlashAttention-2 减少显存占用
pip install -U flash-attn --no-build-isolation
```

#### macOS（Apple Silicon M1/M2/M3/M4）

```bash
# 安装 PyTorch（MPS 支持）
pip install -U torch torchvision torchaudio

# 安装 qwen-tts
pip install -U qwen-tts

# 验证 MPS 可用
python -c "import torch; print('MPS可用' if torch.backends.mps.is_available() else 'MPS不可用')"
```

> Mac 上推荐使用 0.6B 模型，1.7B 在 Mac 上会比较吃力。
> MPS 部分算子可能需要 CPU fallback，脚本已自动设置 `PYTORCH_ENABLE_MPS_FALLBACK=1`。

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

# 测试模型列表
python scripts/clone_voice.py --list
```

---

## Cookie 配置（可选，提升搜索成功率）

B站、YouTube、抖音等平台对无登录访问有反爬限制，提供 cookie 后可直接使用平台搜索，成功率更高。

### Cookie 存放位置

```
~/.hermes/cookies/
├── bilibili.txt    # B站 cookie
├── youtube.txt     # YouTube cookie
└── douyin.txt      # 抖音 cookie
```

脚本会**自动检测**该目录下的 cookie 文件，无需额外参数。也可用 `--cookies` 参数手动指定：
```bash
python scripts/search_audio.py --name "雷军" --source bilibili --cookies /path/to/my_cookies.txt
```

### 如何导出 Cookie

Cookie 文件必须是 **Netscape 格式**（yt-dlp 要求），推荐以下方式导出：

#### 方式一：浏览器扩展导出（推荐）

1. 安装浏览器扩展：
   - Chrome: [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)
2. 登录对应网站（如 bilibili.com）
3. 在该网站页面点击扩展图标，导出 cookies.txt
4. 将导出的文件保存到 `~/.hermes/cookies/bilibili.txt`

#### 方式二：yt-dlp 从浏览器自动读取

如果服务器上有浏览器，可直接让 yt-dlp 读取：
```bash
# 从 Chrome 读取 cookie（需要在有桌面环境的机器上运行）
yt-dlp --cookies-from-browser chrome "bilisearch5:雷军" --dump-json --no-download
```
> 注意：这种方式只适合本地有图形界面的机器，服务器通常没有浏览器。

#### 方式三：手动构造

Cookie 文件格式（每行一条，用 Tab 分隔）：
```
# Netscape HTTP Cookie File
.bilibili.com	TRUE	/	FALSE	0	SESSDATA	你的SESSDATA值
.bilibili.com	TRUE	/	FALSE	0	bili_jct	你的bili_jct值
.bilibili.com	TRUE	/	FALSE	0	DedeUserID	你的UID
```

从浏览器开发者工具（F12 → Application → Cookies）复制对应值即可。

### 各平台关键 Cookie

| 平台 | 关键 Cookie | 获取方式 |
|------|------------|----------|
| **B站** | `SESSDATA`, `bili_jct`, `DedeUserID` | 登录 bilibili.com 后从浏览器获取 |
| **YouTube** | 登录态 cookie（整体导出） | 登录 youtube.com 后整体导出 |
| **抖音** | `sessionid`, `ttwid` | 登录 douyin.com 后从浏览器获取 |

### Cookie 安全提示

- Cookie 等同于你的登录凭据，**不要泄露给他人**
- 服务器上的 cookie 文件建议设置权限：`chmod 600 ~/.hermes/cookies/*.txt`
- Cookie 有过期时间，失效后需要重新导出
- 如果不想配置 cookie，脚本会自动 fallback 到公开网络搜索（DuckDuckGo）

---

## 音频质量建议

克隆效果取决于参考音频质量：

| 项目 | 建议 |
|------|------|
| 时长 | 最少3秒，推荐10-30秒 |
| 格式 | WAV 最佳，MP3 也可 |
| 采样率 | 16kHz 以上 |
| 内容 | 纯人声，无背景音乐/噪声 |
| 语速 | 正常语速，吐字清晰 |

## 常见问题

### Q: 搜索不到某人的音频

- 脚本默认通过搜索引擎查找，无需登录
- 尝试不同关键词：`--keyword "采访"` 或 `--keyword "TED"`
- 也可直接提供视频链接：`--url "https://..."`

### Q: 如何检查是否支持本地克隆

```bash
# Linux 服务器：检查 NVIDIA GPU
nvidia-smi

# Mac：检查 MPS（Apple Silicon）
python -c "import torch; print('MPS可用' if torch.backends.mps.is_available() else 'MPS不可用')"
```

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
