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
