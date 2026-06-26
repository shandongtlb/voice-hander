# 技术规章

本文档定义当前内网语音助手项目的模块边界、文件职责、接口约定和扩展规则。代码实现以“主后端稳定、能力服务可替换、工具执行可审计”为原则。

## 1. 架构原则

1. 主后端只做编排，不内置具体 ASR/TTS 模型。
2. ASR、LLM、TTS 必须通过 adapter 边界调用。
3. 前端只调用主后端，不直接调用模型、ASR、TTS 或工具执行接口。
4. 工具能力必须注册到 ToolRegistry，不能绕过 registry 直接让 LLM 执行本地操作。
5. 命令执行、Windows GUI 操作、截图、OCR 等能力必须保留策略开关和审计记录。
6. `config.yaml` 是本机私有配置，不提交；`config.example.yaml` 只能放可公开的示例值。
7. 后续新增大功能时，优先新增 adapter/tool/service 边界，不把外部服务逻辑塞进 API 路由。

## 2. 服务边界

```text
Vue frontend
  -> FastAPI main API
       -> Agent loop
            -> LLM adapter
            -> Tool registry
            -> Audit store
       -> ASR adapter
       -> TTS adapter

External capability services
  -> ASR service: /transcribe
  -> TTS service: /synthesize
  -> optional remote desktop agents
```

## 3. 文件职责

### 根目录

| 文件 | 职责 |
| --- | --- |
| `README.md` | 项目快速启动说明和当前能力摘要。 |
| `pyproject.toml` | Python 包元数据、依赖、可选 Windows 依赖、测试配置。 |
| `config.example.yaml` | 可提交的配置模板，只允许本地/占位值。 |
| `config.yaml` | 本机真实配置，已被 `.gitignore` 忽略，不应提交。 |
| `.gitignore` | 忽略虚拟环境、私有配置、数据、构建产物。 |
| `start.ps1` | 根目录后端启动入口，委托给 `scripts/start.ps1`。 |
| `start-frontend.ps1` | Vue/Vite 前端启动入口。 |

### 后端 API

| 文件 | 职责 |
| --- | --- |
| `src/intranet_assistant/api/app.py` | FastAPI app factory；定义 `/health`、`/v1/chat`、`/v1/transcribe`、`/v1/voice`。 |
| `src/intranet_assistant/api/schemas.py` | API 请求/响应 Pydantic schema。 |
| `src/intranet_assistant/cli.py` | 后端 CLI；支持 `serve` 启动主 API。 |

### 核心配置和装配

| 文件 | 职责 |
| --- | --- |
| `src/intranet_assistant/core/config.py` | 配置 dataclass、YAML 加载、默认值。 |
| `src/intranet_assistant/core/factory.py` | AppContainer；装配 LLM、ASR、TTS、工具、审计、Agent。 |

### Agent

| 文件 | 职责 |
| --- | --- |
| `src/intranet_assistant/agent/loop.py` | 对话循环、会话内存、tool_calls 执行、审计写入。 |

### Adapter

| 文件 | 职责 |
| --- | --- |
| `src/intranet_assistant/adapters/base.py` | LLM/ASR/TTS 协议和 ChatMessage/LlmResponse 数据结构。 |
| `src/intranet_assistant/adapters/llm/openai_compatible.py` | OpenAI-compatible chat completions 调用，支持 tools/tool_choice。 |
| `src/intranet_assistant/adapters/asr/http_client.py` | 调用外部 ASR HTTP 服务；目标接口是 `POST /transcribe`。 |
| `src/intranet_assistant/adapters/tts/http_client.py` | 调用外部 TTS HTTP 服务；目标接口是 `POST /synthesize`。 |

### 工具系统

| 文件 | 职责 |
| --- | --- |
| `src/intranet_assistant/tools/base.py` | ToolSpec、ToolResult、Tool Protocol。 |
| `src/intranet_assistant/tools/registry.py` | 工具注册、OpenAI tool schema 暴露、工具调用路由。 |
| `src/intranet_assistant/tools/shell.py` | PowerShell/Bash 执行工具，包含危险命令过滤和输出限制。 |
| `src/intranet_assistant/tools/windows.py` | Windows GUI 自动化工具，包含窗口枚举、控件点击、输入、热键、截图、坐标点击、OCR 入口。 |

### 存储

| 文件 | 职责 |
| --- | --- |
| `src/intranet_assistant/storage/audit.py` | SQLite 审计日志写入。当前用于记录用户消息、助手消息、工具结果。 |

### 脚本

| 文件 | 职责 |
| --- | --- |
| `scripts/start.ps1` | 实际后端启动脚本；自动创建 `.venv`、可安装依赖、读取配置并启动 API。 |
| `scripts/chat.ps1` | PowerShell 文本聊天客户端，显式 UTF-8 编码。 |
| `scripts/voice.ps1` | 音频文件客户端；调用 `/v1/voice`。 |
| `scripts/smoke_chat.py` | LLM adapter 冒烟测试脚本。 |
| `scripts/mock_asr.py` | ASR 占位服务；仅用于链路测试，不做真实识别。 |
| `scripts/mock_tts.py` | TTS 占位服务；仅用于链路测试，不做真实合成。 |

### 前端

| 文件 | 职责 |
| --- | --- |
| `frontend/package.json` | 前端依赖和 npm scripts。 |
| `frontend/vite.config.ts` | Vite 开发服务器配置。 |
| `frontend/index.html` | 前端 HTML 入口。 |
| `frontend/src/main.ts` | Vue app 挂载入口。 |
| `frontend/src/App.vue` | 语音工作台页面；录音、分片转写、草稿、chat 会话。 |
| `frontend/src/api.ts` | 前端调用主后端的 API client。 |
| `frontend/src/styles.css` | 前端样式。 |
| `frontend/src/env.d.ts` | Vite 类型声明。 |

### 测试

| 文件 | 职责 |
| --- | --- |
| `tests/test_config.py` | 配置解析测试。 |
| `tests/test_tool_registry.py` | 工具注册和调用路由测试。 |

## 4. API 规约

### 主后端

| 接口 | 方法 | 用途 |
| --- | --- | --- |
| `/health` | `GET` | 返回服务状态、工具列表、adapter provider。 |
| `/v1/chat` | `POST` JSON | 文本进入 Agent。 |
| `/v1/transcribe` | `POST` multipart | 前端上传音频片段，主后端转发给 ASR adapter。 |
| `/v1/voice` | `POST` JSON | 音频 base64 -> ASR -> Agent -> TTS。 |

### `/v1/chat`

请求：

```json
{
  "message": "你好",
  "session_id": "可选"
}
```

响应：

```json
{
  "session_id": "uuid",
  "reply": "回复文本",
  "tool_results": []
}
```

### `/v1/transcribe`

请求：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file` | audio file | 是 | 浏览器录音片段，常见为 `webm/opus`。 |

响应：

```json
{
  "transcript": "识别出的文字"
}
```

## 5. 工具规约

1. 新工具必须实现 `spec` 和 `run(arguments)`。
2. `spec.parameters` 必须是 JSON Schema object。
3. 新工具必须通过 `ToolRegistry.register()` 注册。
4. 会修改系统状态的工具必须有明确配置开关或安全策略。
5. 工具返回必须使用 `ToolResult`，错误不能直接抛给 Agent 主循环。
6. 坐标点击只能作为兜底，不得优先于 UI Automation 控件操作。
7. OCR、截图、鼠标键盘模拟都应视为敏感能力，需要在配置和文档中明确说明。

## 6. 配置规约

1. `config.example.yaml` 只允许示例地址、示例 key、默认本地端口。
2. `config.yaml` 可包含真实模型地址和 key，但必须留在 `.gitignore` 中。
3. ASR/TTS 默认作为外部服务存在，主后端只读取 `asr.base_url` 和 `tts.base_url`。
4. 前端跨域来源统一放在 `server.cors_origins`。
5. Windows 工具危险项默认关闭，例如坐标点击和 OCR。

## 7. 启动规约

常规开发需要三个进程：

```powershell
.\start.ps1
.\start-frontend.ps1
.\.venv\Scripts\python.exe -m uvicorn scripts.mock_asr:app --host 127.0.0.1 --port 8101
```

如果接入真实 ASR，把第三个进程替换成真实 ASR 服务，保持 `POST /transcribe` 契约不变。

## 8. 安全规约

1. 不在仓库提交任何真实 API key、内网凭据、摄像头地址、RTSP 密码。
2. 对外暴露服务前必须增加鉴权、IP 白名单、操作审计和危险动作确认。
3. 监控软件、远程桌面、命令执行等能力不得直接暴露给前端。
4. LLM 只能通过已注册工具操作系统，不能绕过策略执行任意代码。
5. 操作 Windows GUI 前应优先读取窗口/控件树，再考虑 OCR/图像识别，最后才坐标点击。

## 9. 后续扩展规则

1. 新 provider 放在 `adapters/<domain>/`。
2. 新本地能力放在 `tools/`，并由 `core/factory.py` 注册。
3. 新独立服务优先放在 `scripts/` 做 PoC，稳定后再提升到正式 package。
4. 前端新增 API 调用必须先在 `frontend/src/api.ts` 封装。
5. 重大能力需要同步更新 `README.md`、本文档和接口清单。
