---
name: voice-tts
description: 文字转语音合成与语音消息发送。当用户要求 agent 说话、发语音、朗读文字、语音回复、克隆声音时使用。支持 edge-tts（免费，400+ 音色）和 Fish Audio（语音克隆）。通过飞书发送语音消息，可扩展到其他平台。
version: 0.1.0
required_environment_variables:
  - FEISHU_APP_ID
  - FEISHU_APP_SECRET
metadata:
  hermes:
    category: media
    tags:
      - voice
      - tts
      - feishu
      - speech
      - 语音
---

# 语音合成与发送（Voice TTS）

让 agent 能"说话"：将文字合成为语音，并通过飞书发送语音消息。

## 前置条件

首次使用前需安装依赖，详见 [setup.md](setup.md)。

## 核心脚本

所有脚本位于 `scripts/` 目录下，通过命令行调用。

### 1. 发送语音消息

```bash
python scripts/speak.py --text "要说的内容" --target "ou_用户open_id" --voice "zh-CN-XiaoxiaoNeural"
```

参数说明：
| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--text` | 是 | - | 要合成的文字 |
| `--target` | 是 | - | 接收人 ID（open_id 或 chat_id） |
| `--voice` | 否 | zh-CN-XiaoxiaoNeural | 音色名称 |
| `--platform` | 否 | feishu | 发送平台（feishu / local） |
| `--receive-type` | 否 | open_id | ID 类型（open_id / chat_id） |

发到群聊：
```bash
python scripts/speak.py --text "群聊语音" --target "oc_群聊chat_id" --receive-type chat_id
```

仅合成不发送（保存到本地）：
```bash
python scripts/speak.py --text "测试合成" --target test --platform local --output-dir /tmp/voice
```

### 2. 列出可用音色

```bash
python scripts/voices.py
python scripts/voices.py --locale zh-CN    # 仅中文
python scripts/voices.py --locale en-US    # 仅英文
```

### 3. 语音克隆（Fish Audio）

需要设置环境变量 `FISH_AUDIO_API_KEY`（在 https://fish.audio 免费注册，每天 1 万字免费额度）。

```bash
# 使用已创建的声音模型
python scripts/speak.py --text "克隆声音说话" --target "ou_xxx" --engine fish --fish-model-id "模型ID"

# 零样本克隆：提供一段参考音频（10-30 秒）
python scripts/speak.py --text "克隆声音" --target "ou_xxx" --engine fish --reference-audio "/path/to/sample.wav"
```

## 常用音色

| 音色 | 性别 | 风格 |
|------|------|------|
| zh-CN-XiaoxiaoNeural | 女 | 温暖亲切（默认） |
| zh-CN-YunxiNeural | 男 | 年轻休闲 |
| zh-CN-XiaoyiNeural | 女 | 活泼开朗 |
| zh-CN-YunjianNeural | 男 | 沉稳权威 |
| zh-CN-YunyangNeural | 男 | 新闻播报 |
| zh-CN-XiaomoNeural | 女 | 故事讲述 |
| zh-CN-XiaoshuangNeural | 女 | 童声 |

完整列表运行 `python scripts/voices.py`。

## 调用示例

agent 在处理用户请求时，按以下方式调用：

**用户说"用语音回复我"：**
```bash
python scripts/speak.py --text "这是语音回复内容" --target "ou_用户ID"
```

**用户说"用男声回复"：**
```bash
python scripts/speak.py --text "回复内容" --target "ou_用户ID" --voice zh-CN-YunxiNeural
```

**用户说"在群里发条语音"：**
```bash
python scripts/speak.py --text "群聊内容" --target "oc_群聊ID" --receive-type chat_id
```
