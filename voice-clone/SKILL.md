---
name: voice-clone
description: 声音克隆技能。支持从网络搜索公众人物音频或上传本地音频，通过 Qwen3-TTS（本地）或 Fish Audio（云端）创建声音模型。自动检测 GPU：有 GPU 优先用 Qwen3-TTS 本地克隆（3秒音频即可），无 GPU 回退 Fish Audio 云端。当用户要求克隆声音、模仿某人说话、创建声音模型时使用。
version: 0.2.0
metadata:
  hermes:
    category: media
    tags:
      - voice
      - clone
      - tts
      - 声音克隆
      - qwen3-tts
---

# 声音克隆（Voice Clone）

从网络搜索公众人物音频或上传本地音频，创建专属声音模型，配合 `voice-tts` 技能用克隆的声音发语音消息。

## 克隆引擎

| 引擎 | 优先级 | 条件 | 特点 |
|------|--------|------|------|
| **Qwen3-TTS** | 优先 | GPU + `pip install qwen-tts` | 本地推理，3秒音频即可克隆，免费无限制 |
| **Fish Audio** | 备选 | `FISH_AUDIO_API_KEY` | 云端 API，免费额度每天1万字 |

脚本自动检测环境并选择引擎，也可通过 `--engine qwen` 或 `--engine fish` 手动指定。

## 前置条件

首次使用前需安装依赖，详见 [setup.md](setup.md)。

## 工作流程

```
搜索/上传音频 → 音频处理（裁剪、降噪） → 创建声音模型（本地或云端） → 用 voice-tts 发送克隆语音
```

## 核心脚本

所有脚本位于 `scripts/` 目录下。

### 1. 从网络搜索公众人物音频

默认通过公开搜索引擎查找视频，**无需登录**。提供 cookie 后可直接使用平台搜索，成功率更高。

| 搜索方式 | `--source` 值 | 说明 |
|----------|--------------|------|
| **网络搜索** | `web`（默认） | 通过搜索引擎查找 B站/抖音/YouTube 视频，无需登录 |
| **B站** | `bilibili` | 通过 yt-dlp bilisearch 直接搜索（有 cookie 效果最好，无 cookie 会自动回退到网络搜索） |
| **YouTube** | `youtube` | 通过 yt-dlp ytsearch 搜索 |
| **直接链接** | `--url` | 提供任意视频/音频 URL 直接下载 |

```bash
python scripts/search_audio.py --name "人物名字"
```

参数说明：
| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--name` | 搜索模式必填 | - | 公众人物姓名 |
| `--source` | 否 | web | 搜索方式：web / bilibili / youtube |
| `--url` | URL模式必填 | - | 直接提供视频/音频链接 |
| `--cookies` | 否 | 自动检测 | cookie 文件路径（Netscape 格式），不指定时自动查找 `~/.hermes/cookies/` |
| `--output-dir` | 否 | ./audio_samples | 音频保存目录 |
| `--max-results` | 否 | 5 | 最大搜索结果数 |
| `--keyword` | 否 | 演讲 | 附加搜索关键词（演讲/采访/朗读） |

**Cookie 自动加载：** 脚本会自动检测 `~/.hermes/cookies/` 下的平台 cookie 文件（如 `bilibili.txt`、`youtube.txt`、`douyin.txt`），用于搜索和下载。详见 [setup.md](setup.md) 中的 Cookie 配置说明。

示例：
```bash
# 搜索雷军的演讲音频（默认网络搜索，无需登录）
python scripts/search_audio.py --name "雷军" --keyword "演讲"

# 使用 B站搜索（有 cookie 时直接搜索，无 cookie 自动回退到网络搜索）
python scripts/search_audio.py --name "雷军" --source bilibili

# 手动指定 cookie 文件
python scripts/search_audio.py --name "雷军" --source bilibili --cookies ~/.hermes/cookies/bilibili.txt

# 搜索罗翔的讲课
python scripts/search_audio.py --name "罗翔" --keyword "讲课"

# 搜索国际人物
python scripts/search_audio.py --name "Elon Musk" --keyword "interview"

# 直接下载 B站/抖音/YouTube 视频音频（有 cookie 自动加载）
python scripts/search_audio.py --url "https://www.bilibili.com/video/BVxxxxxx"
python scripts/search_audio.py --url "https://www.douyin.com/video/xxxxxx"
python scripts/search_audio.py --url "https://www.youtube.com/watch?v=xxxxxx"
```

### 2. 处理音频（格式转换、裁剪、降噪）

将搜索到或上传的原始音频处理为适合克隆的格式：

```bash
python scripts/prepare_audio.py --input raw_audio.mp4 --output prepared.wav
```

参数说明：
| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | 是 | - | 原始音频/视频文件路径 |
| `--output` | 否 | prepared.wav | 输出文件路径 |
| `--start` | 否 | 0 | 裁剪起始时间（秒） |
| `--duration` | 否 | 30 | 裁剪时长（秒），Qwen3-TTS 最少3秒，建议10-30秒 |
| `--denoise` | 否 | false | 是否降噪处理 |

示例：
```bash
# 从视频中截取 10-40 秒的片段
python scripts/prepare_audio.py --input interview.mp4 --start 10 --duration 30

# 处理并降噪
python scripts/prepare_audio.py --input noisy_audio.mp3 --denoise

# 处理用户上传的音频
python scripts/prepare_audio.py --input /path/to/uploaded_audio.wav --duration 20
```

### 3. 创建声音模型

自动选择引擎（有GPU用Qwen3-TTS，否则用Fish Audio）：

```bash
python scripts/clone_voice.py --audio prepared.wav --name "模型名称"
```

参数说明：
| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--audio` | 创建时必填 | - | 音频文件（可多个） |
| `--name` | 创建时必填 | - | 声音模型名称 |
| `--engine` | 否 | auto | 克隆引擎：auto / qwen / fish |
| `--tts` | 否 | - | 使用本地模型合成语音 |
| `--model` | 合成时必填 | - | 本地模型名称（配合 --tts） |
| `--text` | 合成时必填 | - | 合成文本（配合 --tts） |
| `--output` | 否 | output.wav | 输出文件（配合 --tts） |
| `--list` | 否 | - | 列出所有模型（本地+云端） |
| `--delete` | 否 | - | 删除 Fish Audio 云端模型 |

示例：
```bash
# 创建声音模型（自动选引擎）
python scripts/clone_voice.py --audio prepared.wav --name "雷军-演讲"

# 指定用本地 Qwen3-TTS
python scripts/clone_voice.py --audio prepared.wav --name "雷军" --engine qwen

# 指定用云端 Fish Audio
python scripts/clone_voice.py --audio prepared.wav --name "雷军" --engine fish

# 用本地模型直接合成语音
python scripts/clone_voice.py --tts --model "雷军" --text "Are you OK" --output test.wav

# 列出所有模型
python scripts/clone_voice.py --list
```

### 4. 用克隆声音发语音消息

**本地模型（Qwen3-TTS）：**
```bash
# 先合成到文件
python scripts/clone_voice.py --tts --model "雷军" --text "你好" --output /tmp/hello.wav

# 再用 voice-tts 发送
python voice-tts/scripts/speak.py --text "你好" --target "ou_xxx" --engine qwen --ref-audio "~/.hermes/voice-models/雷军/prepared.wav"
```

**云端模型（Fish Audio）：**
```bash
python voice-tts/scripts/speak.py \
    --text "用克隆的声音说话" \
    --target "ou_xxx" \
    --engine fish \
    --fish-model-id "创建得到的模型ID"
```

## 完整使用示例

### 示例一：克隆公众人物声音

```bash
# 步骤 1：搜索音频（有 cookie 自动使用，无 cookie 走网络搜索）
python scripts/search_audio.py --name "雷军" --keyword "演讲"

# 步骤 2：处理音频
python scripts/prepare_audio.py --input ./audio_samples/xxx.wav --start 5 --duration 25

# 步骤 3：创建模型（自动选引擎）
python scripts/clone_voice.py --audio prepared.wav --name "雷军"

# 步骤 4：使用
# Qwen3-TTS 本地：
python scripts/clone_voice.py --tts --model "雷军" --text "Are you OK" --output /tmp/test.wav
# Fish Audio 云端：
python voice-tts/scripts/speak.py --text "Are you OK" --target "ou_xxx" --engine fish --fish-model-id "模型ID"
```

### 示例二：直接链接克隆

```bash
python scripts/search_audio.py --url "https://www.bilibili.com/video/BVxxxxxx"
python scripts/prepare_audio.py --input ./audio_samples/xxx.wav --duration 25 --denoise
python scripts/clone_voice.py --audio prepared.wav --name "目标声音"
```

### 示例三：用户上传音频克隆

```bash
python scripts/prepare_audio.py --input /path/to/uploaded.mp3 --duration 20 --denoise
python scripts/clone_voice.py --audio prepared.wav --name "我的声音"
```

## 调用示例

agent 在处理用户请求时，按以下方式调用：

**用户说"帮我克隆雷军的声音"：**
1. 调用 `search_audio.py --name "雷军"` 搜索音频
2. 调用 `prepare_audio.py` 处理音频
3. 调用 `clone_voice.py --audio prepared.wav --name "雷军"` 创建模型（自动选引擎）
4. 返回结果给用户

**用户给了一个视频链接说"用这个视频里的声音克隆"：**
1. 调用 `search_audio.py --url "链接"` 直接下载
2. 调用 `prepare_audio.py` 处理
3. 调用 `clone_voice.py` 创建模型

**用户上传了一段音频说"用这个声音克隆"：**
1. 调用 `prepare_audio.py --input 上传的文件` 处理
2. 调用 `clone_voice.py` 创建模型

**用户说"用雷军的声音说 xxx"：**
1. 调用 `clone_voice.py --list` 查看是否已有模型
2. 如果有本地模型：`clone_voice.py --tts --model "雷军" --text "xxx" --output /tmp/out.wav`
3. 如果有 Fish Audio 模型：`voice-tts/scripts/speak.py --engine fish --fish-model-id 模型ID --text "xxx"`
4. 如果没有模型，先走克隆流程再发送
