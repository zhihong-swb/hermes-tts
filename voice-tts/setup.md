# 安装与配置指南

## 目录

- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
- [飞书机器人配置](#飞书机器人配置)
- [语音克隆配置（可选）](#语音克隆配置可选)
- [部署到不同平台](#部署到不同平台)
- [常见问题](#常见问题)

---

## 环境要求

- Python >= 3.9
- ffmpeg（音频格式转换）
- 网络连接（Edge TTS 和飞书 API 需要）

## 安装步骤

### 1. 安装 ffmpeg

```bash
# macOS
brew install ffmpeg

# CentOS / Alibaba Cloud Linux
yum install -y ffmpeg

# Ubuntu / Debian
apt install -y ffmpeg

# 验证
ffmpeg -version
```

### 2. 安装 Python 依赖

```bash
# 在你的 agent 的 Python 环境中安装
pip install edge-tts httpx

# 如果 agent 使用 venv，需要指定路径，例如 hermes：
/home/admin/.hermes/hermes-agent/venv/bin/python3 -m pip install edge-tts httpx
```

### 3. 复制 skill 到 agent 的 skills 目录

```bash
# Hermes Agent
cp -r voice-tts ~/.hermes/skills/

# Claude Code
cp -r voice-tts ~/.claude/skills/

# OpenClaw
cp -r voice-tts ~/.openclaw/skills/

# Qoder
cp -r voice-tts ~/.qoder/skills/
```

### 4. 验证安装

```bash
# 测试合成（保存到本地，不发飞书）
python ~/.hermes/skills/voice-tts/scripts/speak.py \
    --text "安装测试成功" \
    --target test \
    --platform local \
    --output-dir /tmp/tts_test

# 测试列出音色
python ~/.hermes/skills/voice-tts/scripts/voices.py
```

---

## 飞书机器人配置

### 已有飞书机器人

如果 hermes 已配置飞书机器人（`.env` 中有 `FEISHU_APP_ID`），无需额外配置，脚本会自动读取环境变量。

确认环境变量已加载：
```bash
# 查看当前配置
grep FEISHU ~/.hermes/.env

# 如果 shell 中没加载，手动加载
export $(grep -E '^FEISHU_(APP_ID|APP_SECRET)' ~/.hermes/.env | xargs)
```

### 新建飞书机器人

1. 打开 [飞书开放平台](https://open.feishu.cn/app)，创建企业自建应用
2. 获取 **App ID** 和 **App Secret**
3. 在「权限管理」中添加以下权限：
   - `im:message:send_as_bot` - 发送消息
   - `im:file` - 上传文件
   - `im:resource` - 访问资源
4. 配置环境变量：

```bash
# 写入 ~/.hermes/.env（hermes 会自动加载）
echo 'FEISHU_APP_ID=你的app_id' >> ~/.hermes/.env
echo 'FEISHU_APP_SECRET=你的app_secret' >> ~/.hermes/.env

# 或者写入 ~/.bashrc（所有程序可用）
echo 'export FEISHU_APP_ID=你的app_id' >> ~/.bashrc
echo 'export FEISHU_APP_SECRET=你的app_secret' >> ~/.bashrc
source ~/.bashrc
```

### 获取用户 open_id

发送语音需要知道接收人的 open_id，获取方式：

1. 在飞书开放平台 → 你的应用 → API 调试台
2. 调用「获取用户信息」接口
3. 或从 hermes 的 session 日志中查找：
   ```bash
   grep -r "open_id" ~/.hermes/sessions/ | head -5
   ```

---

## 语音克隆配置（可选）

### Fish Audio（推荐，简单免费）

1. 访问 https://fish.audio 注册账号
2. 获取 API Key（免费额度：每天 10,000 字）
3. 配置：

```bash
export FISH_AUDIO_API_KEY="你的api_key"
```

#### 创建专属声音模型

1. 准备 10-30 秒清晰语音样本（WAV 格式，无背景噪音）
2. 在 https://fish.audio 上传创建模型
3. 获取模型 ID，使用：

```bash
python scripts/speak.py --text "测试" --target "ou_xxx" --engine fish --fish-model-id "你的模型ID"
```

#### 零样本克隆（无需预创建模型）

```bash
python scripts/speak.py \
    --text "克隆的声音" \
    --target "ou_xxx" \
    --engine fish \
    --reference-audio "/path/to/sample.wav" \
    --reference-text "参考音频的文字内容"
```

### CosyVoice / GPT-SoVITS（本地部署）

如需完全离线的语音克隆，可部署以下开源项目：

- **CosyVoice**：https://github.com/FunAudioLLM/CosyVoice（阿里开源，需 GPU）
- **GPT-SoVITS**：https://github.com/RVC-Boss/GPT-SoVITS（社区热门，需 GPU）

部署后可修改 `speak.py` 添加对应引擎支持。

---

## 部署到不同平台

### Hermes Agent

```bash
# 安装依赖到 hermes 的 venv
/home/admin/.hermes/hermes-agent/venv/bin/python3 -m ensurepip 2>/dev/null
/home/admin/.hermes/hermes-agent/venv/bin/python3 -m pip install edge-tts httpx

# 复制 skill
cp -r voice-tts ~/.hermes/skills/

# 飞书凭证已在 ~/.hermes/.env 中，hermes 运行时自动加载
# 验证
/home/admin/.hermes/hermes-agent/venv/bin/python3 ~/.hermes/skills/voice-tts/scripts/speak.py \
    --text "Hermes TTS 测试" --target test --platform local --output-dir /tmp/test
```

### Claude Code / Qoder

```bash
# 安装 Python 依赖
pip install edge-tts httpx

# 复制到对应 skills 目录
cp -r voice-tts ~/.claude/skills/    # Claude Code
cp -r voice-tts ~/.qoder/skills/     # Qoder

# 设置环境变量
export FEISHU_APP_ID="xxx"
export FEISHU_APP_SECRET="xxx"
```

---

## 常见问题

### Q: 提示 "ffmpeg not found"

安装 ffmpeg：
```bash
yum install -y ffmpeg    # CentOS
apt install -y ffmpeg    # Ubuntu
brew install ffmpeg      # macOS
```

### Q: 提示 "No module named edge_tts"

确保安装到了 agent 使用的 Python 环境中：
```bash
# 查看 agent 用的哪个 python
which python3
# 用那个 python 安装
/path/to/python3 -m pip install edge-tts httpx
```

### Q: 飞书发送失败 "token error"

检查环境变量是否正确加载：
```bash
echo $FEISHU_APP_ID
echo $FEISHU_APP_SECRET
```

### Q: 飞书发送失败 "permission denied"

确认机器人有 `im:message:send_as_bot` 和 `im:file` 权限，且已发布上线。

### Q: 语音克隆效果不好

- 参考音频建议 10-30 秒，纯语音，无背景音乐
- 提供 `--reference-text` 可提高克隆质量
- WAV 格式、16kHz 以上采样率效果更佳
