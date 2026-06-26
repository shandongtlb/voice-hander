# 待实现接口清单

本文档只列“需要对接或后续实现的接口”，不代表当前已经完成。

## 1. ASR 服务接口

当前主后端已经假定存在一个 ASR HTTP 服务：

```text
POST {asr.base_url}/transcribe
Content-Type: multipart/form-data
```

请求字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file` | audio file | 是 | 音频文件或浏览器录音片段。 |
| `language` | string | 否 | 默认 `zh`。 |

响应：

```json
{
  "text": "识别出的文字"
}
```

待做：

- 接入真实本地 ASR，例如 Whisper、faster-whisper、sherpa-onnx、FunASR。
- 支持浏览器 `audio/webm; codecs=opus`。
- 支持长音频切片、静音检测、增量转写。
- 返回置信度、时间戳、语言、分段结果。
- 增加 ASR `/health`。
- 增加 ASR 错误码规范。

## 2. TTS 服务接口

当前主后端已经假定存在一个 TTS HTTP 服务：

```text
POST {tts.base_url}/synthesize
Content-Type: application/json
```

请求：

```json
{
  "text": "要合成的文本",
  "voice": "default"
}
```

响应：

```text
audio/wav bytes
```

待做：

- 接入真实本地 TTS，例如 Piper、Edge-TTS 离线替代、CosyVoice、ChatTTS。
- 支持音色列表接口。
- 支持流式音频返回。
- 支持中文标点和数字规范化。
- 增加 TTS `/health`。

## 3. 监控软件操作接口

不要让 LLM 直接猜坐标点击监控软件。应封装成明确工具接口：

```text
search_camera(keyword)
open_camera(name_or_id)
list_camera_groups()
switch_layout(layout)
snapshot_current_view()
inspect_monitor_app()
```

推荐策略顺序：

1. 监控平台 SDK/API/ONVIF/RTSP。
2. Windows UI Automation 控件树。
3. OCR 识别文字位置。
4. 图像模板匹配。
5. 坐标点击兜底。

待做：

- 定义摄像头目录数据结构。
- 定义监控软件窗口识别规则。
- 实现 `inspect_monitor_app`，输出窗口标题、控件树、截图路径、OCR 文本。
- 为危险操作增加确认策略。

## 4. 远程桌面 Agent 接口

如果要控制另一台独立 Windows 主机，应在被控机器上部署轻量 Agent，而不是从本机直接 pywinauto。

建议接口：

```text
GET  /health
POST /tools/list_windows
POST /tools/inspect_window
POST /tools/screenshot
POST /tools/ocr_screen
POST /tools/click_control
POST /tools/type_text
POST /tools/hotkey
POST /tools/open_camera
```

待做：

- Token 鉴权。
- IP 白名单。
- 操作审计。
- 只暴露白名单业务动作。
- 禁止默认开放任意 PowerShell。

## 5. OCR/视觉接口

当前项目只保留 OCR 工具入口，Python 3.14 环境下 `rapidocr-onnxruntime` 未安装。

待做：

- 确定 OCR 引擎和 Python 版本。
- 定义 OCR 返回格式：文本、置信度、矩形框、截图路径。
- 增加图像模板匹配接口。
- 可选接入本地多模态模型，对截图做摘要。

## 6. 会话持久化接口

当前会话历史存在内存中，重启后丢失；SQLite 只做审计。

待做：

- `GET /v1/sessions`
- `GET /v1/sessions/{session_id}`
- `DELETE /v1/sessions/{session_id}`
- 从审计日志恢复会话上下文。
- 限制单会话最大历史长度和保留周期。

## 7. 权限确认接口

当前系统 prompt 要求危险动作确认，但还没有独立确认流。

待做：

- `POST /v1/actions/propose`
- `POST /v1/actions/{action_id}/approve`
- `POST /v1/actions/{action_id}/reject`
- 前端展示待确认动作。
- 工具执行前检查批准状态。
