# ACE Studio WebBridge REST API

> ⚠️ **Developer Preview**  
> 该文档和对应的 Feature 目前处于 Developer Preview 状态，会进行比较频繁的修改和迭代，暂不保证 API 的稳定性。

## 概述

WebBridge REST API 是 ACE Studio 提供的本地 HTTPS REST 服务器，用于服务在 Studio 内嵌的 WebView 中的 Web 内容。该服务提供了与 ACE Studio 之间的音频数据交换等能力，可用于 AI 音乐生成等需要在网页端与客户端之间传递音频数据的场景。

## 主要特性

- **HTTPS 加密传输** — 使用自签名证书（WKWebKit 安全要求上严格不允许混合 HTTP 和 HTTPS 内容）
- **Token 身份验证** — Bearer Token 认证机制
- **固定端口** — 21573（可以日后改为动态 + URL 参数提供）

## 服务器信息

| 属性 | 值 |
|------|-----|
| 基础 URL | `https://localhost:21573` |
| 协议 | HTTPS（自签名证书，该证书会被 Studio 的 WebView 自动信任） |
| 端口 | 21573（目前固定，日后可能会改为动态 + URL 参数提供） |

## 身份验证

除 `/api/version` 外，所有 API 端点都需要身份验证。认证方式为 Bearer Token，需要在请求头中携带：

```
Authorization: Bearer <token>
```

### Token 获取方式

ACE Studio 提供两种方式将 Token 传递给 WebView，前端可根据实际需求选择最适合的方案：

#### 方式一：URL 查询参数

ACE Studio 在加载 WebView URL 时，会自动将 token 作为查询参数附加到 URL 中：

```
https://your-web-app.com/page?token=abc123def456...
```

前端可以通过解析 URL 参数获取 token：

```javascript
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');
```

#### 方式二：JavaScript 注入

ACE Studio 在页面加载完成后，通过 JavaScript 将 token 注入到 window 对象：

```javascript
// ACE Studio 会自动执行以下代码
window.ACEStudioToken = 'abc123def456...';
```

前端可以直接从 window 对象读取：

```javascript
const token = window.ACEStudioToken;
```

> 💡 **提示**：两种方式不会同时使用，Studio 侧会根据最终讨论决策来使用其中一种。

### Token 存储建议

目前，Studio 在设计上只会在第一次加载页面时提供 Token。所以，无论最终使用哪种方式获取 Token，建议前端在获取后立即存储到 `sessionStorage` 中，这样可以避免页面刷新或内部导航时丢失 Token。

---

## API 端点

### GET /api/version

健康检查端点，**无需身份验证**。用于检查服务器是否正常运行。

**响应示例：**

```json
{
  "version": "1.0.0",
  "appVersion": "2.0.2.0",
  "status": "ready"
}
```

---

### POST /api/audio/import

音频导入端点（将数据从 Web 转到 Studio），支持从 URL 下载音频。导入过程是异步的，导入完成后音频会保存到项目的 `Samples/Clipboard` 文件夹，并自动设置到 ACE Studio 剪贴板。

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | string | ✅ | 音频文件的 URL 地址 |
| filename | string | ❌ | 自定义文件名 |

**请求示例：**

```json
{
  "url": "https://example.com/audio.wav",
  "filename": "my_audio.wav"
}
```

**成功响应：**

```json
{
  "success": true,
  "taskId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

**错误响应：**

```json
{
  "success": false,
  "error": "Missing 'url' parameter"
}
```

---

### GET /api/audio/import/status

查询音频导入任务的状态。

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | ✅ | 导入任务的 taskId |

**成功响应（进行中）：**

```json
{
  "taskId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "downloading",
  "progress": 45,
  "success": true
}
```

**成功响应（已完成）：**

```json
{
  "taskId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "success": true,
  "filename": "my_audio.wav",
  "clipboardSet": true
}
```

**错误响应：**

```json
{
  "taskId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "progress": 10,
  "success": false,
  "error": "Connection timeout"
}
```

---

### GET /api/audio/clipboard/check

检查剪贴板中是否有音频数据，并获取元数据信息。

**响应示例（有音频）：**

```json
{
  "hasAudio": true,
  "filename": "Clipboard_1.1.0_20241224_123456.wav",
  "mimeType": "audio/wav",
  "size": 1234567
}
```

**响应示例（无音频）：**

```json
{
  "hasAudio": false
}
```

---

### GET /api/audio/clipboard/data

获取剪贴板中的音频数据。该接口返回音频文件的二进制流，类似一个在该服务器上 host 的资源文件。

**成功响应：**

该接口直接返回音频文件的二进制数据。

响应头示例：

```
Content-Type: audio/wav (或对应的 MIME 类型)
Content-Disposition: attachment; filename="Clipboard_...wav"
Access-Control-Expose-Headers: Content-Disposition
```

前端可以使用 `fetch` 或 `<a>` 标签直接下载或处理该二进制流。

**错误响应（无音频）：**

```json
{
  "success": false,
  "error": "No audio in clipboard"
}
```

---

### POST /api/audio/upload

> ℹ️ **该端点尚未实现**，预留用于后续将剪贴板音频上传到 OSS 的功能。

**当前响应：**

```json
{
  "success": false,
  "error": "Upload endpoint not yet implemented - requires backend support"
}
```

---

## 错误处理

所有错误响应都采用统一的 JSON 格式：

```json
{
  "success": false,
  "error": "错误描述信息"
}
```

### 常见 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 OK | 请求成功 |
| 400 Bad Request | 请求参数错误 |
| 401 Unauthorized | Token 无效或缺失 |
| 404 Not Found | 资源不存在（如剪贴板无音频） |
| 500 Internal Server Error | 服务器内部错误 |
| 501 Not Implemented | 功能未实现 |

---

## 注意事项

- **HTTPS 证书**：由于使用自签名证书，如果使用浏览器调试可能会显示安全警告。在 ACE Studio 的 WebView 中，证书已被端侧自动信任，无需额外处理。

- **跨域请求**：服务器已配置 CORS，允许来自 WebView 的跨域请求。

- **Token 安全**：Token 仅在内存中存储，每次 WebView 会话会生成新的 Token。请勿将 Token 持久化存储或泄露给第三方。

- **大文件处理**：对于大型音频文件，建议使用 URL 模式导入，以避免浏览器内存压力并提高传输稳定性。获取剪贴板数据时，二进制流方式也比 Base64 更加高效。