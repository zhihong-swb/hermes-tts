---
name: voice-clone
description: 声音克隆技能。支持从网络搜索公众人物音频或上传本地音频，通过 Fish Audio 创建声音模型，配合 voice-tts 技能用克隆的声音发送语音消息。当用户要求克隆声音、模仿某人说话、创建声音模型时使用。
version: 0.1.0
required_environment_variables:
  - FISH_AUDIO_API_KEY
metadata:
  hermes:
    category: media
    tags:
      - voice
      - clone
      - tts
      - 声音克隆
---

# 声音克隆（Voice Clone）

从网络搜索公众人物音频或上传本地音频，创建专属声音模型，配合 `voice-tts` 技能用克隆的声音发语音消息。

## 前置条件

首次使用前需安装依赖，详见 [setup.md](setup.md)。

## 工作流程

```
搜索/上传音频 -> 音频处理（格式转换、裁剪、降噪） -> 上传 Fish Audio 创建模型 -> 获得模型 ID -> 用 voice-tts 发送克隆语音
```

## 核心脚本

所有脚本位于 `scripts/` 目录下。

### 1. 从网络搜索公众人物音频

搜索公众人物的演讲、采访等音频并下载：

```bash
python scripts/search_audio.py --name "人物名字" --output-dir ./audio_samples
```

参数说明：
| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--name` | 是 | - | 公众人物姓名 |
| `--output-dir` | 否 | ./audio_samples | 音频保存目录 |
| `--max-results` | 否 | 5 | 最大搜索结果数 |
| `--keyword` | 否 | 演讲 | 附加搜索关键词（演讲/采访/朗读） |

示例：
```bash
# 搜索雷军的演讲音频
python scripts/search_audio.py --name "雷军" --keyword "演讲"

# 搜索 Elon Musk 的采访音频
python scripts/search_audio.py --name "Elon Musk" --keyword "interview"
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
| `--duration` | 否 | 30 | 裁剪时长（秒），建议 10-30 秒 |
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

将处理好的音频上传到 Fish Audio 创建克隆模型：

```bash
python scripts/clone_voice.py --audio prepared.wav --name "模型名称"
```

参数说明：
| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--audio` | 是 | - | 处理好的音频文件（可多个） |
| `--name` | 是 | - | 声音模型名称 |
| `--description` | 否 | - | 模型描述 |
| `--list` | 否 | - | 列出已创建的模型 |
| `--delete` | 否 | - | 删除指定模型 ID |

示例：
```bash
# 创建声音模型
python scripts/clone_voice.py --audio prepared.wav --name "雷军-演讲"

# 用多个音频样本创建（效果更好）
python scripts/clone_voice.py --audio sample1.wav sample2.wav --name "自定义声音"

# 列出已有模型
python scripts/clone_voice.py --list

# 删除模型
python scripts/clone_voice.py --delete "模型ID"
```

### 4. 用克隆声音发语音消息

模型创建成功后会返回模型 ID，配合 `voice-tts` 技能使用：

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
# 步骤 1：搜索音频
python scripts/search_audio.py --name "雷军" --keyword "演讲"

# 步骤 2：处理音频（截取清晰片段）
python scripts/prepare_audio.py --input ./audio_samples/xxx.mp3 --start 5 --duration 25

# 步骤 3：创建模型
python scripts/clone_voice.py --audio prepared.wav --name "雷军-演讲"
# 输出：模型 ID: xxxxxxxx

# 步骤 4：用克隆声音发飞书语音
python voice-tts/scripts/speak.py --text "Are you OK" --target "ou_xxx" --engine fish --fish-model-id "xxxxxxxx"
```

### 示例二：用户上传音频克隆

```bash
# 步骤 1：处理上传的音频
python scripts/prepare_audio.py --input /path/to/uploaded.mp3 --duration 20 --denoise

# 步骤 2：创建模型
python scripts/clone_voice.py --audio prepared.wav --name "我的声音"

# 步骤 3：使用
python voice-tts/scripts/speak.py --text "这是我克隆的声音" --target "ou_xxx" --engine fish --fish-model-id "模型ID"
```

## 调用示例

agent 在处理用户请求时，按以下方式调用：

**用户说"帮我克隆雷军的声音"：**
1. 调用 `search_audio.py --name "雷军"` 搜索音频
2. 调用 `prepare_audio.py` 处理音频
3. 调用 `clone_voice.py` 创建模型
4. 返回模型 ID 给用户

**用户上传了一段音频说"用这个声音克隆"：**
1. 调用 `prepare_audio.py --input 上传的文件路径` 处理
2. 调用 `clone_voice.py` 创建模型
3. 返回模型 ID

**用户说"用雷军的声音说 xxx"：**
1. 如果已有模型，直接调用 `voice-tts/scripts/speak.py --engine fish --fish-model-id 模型ID`
2. 如果没有模型，先走克隆流程再发送
