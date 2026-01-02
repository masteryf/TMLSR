# TMLSR API 文档

本文档详细描述了 TMLSR 服务提供的 RESTful API 接口。

**Base URL**: `http://localhost:6008` (默认)

## 📋 接口列表

### 1. 提交任务

创建一个新的超分任务。

- **URL**: `/tasks`
- **Method**: `POST`
- **Content-Type**: `application/json`

**请求参数**:

| 字段 | 类型 | 必选 | 描述 |
|------|------|------|------|
| `url` | string | 是 | 输入文件的 HTTP URL 地址（支持图片或视频） |
| `type` | string | 否 | 任务类型，`video` 或 `image` (默认: `video`) |
| `workflow` | string | 否 | 指定使用的工作流文件名 (例如 `seedvr2_image_4096.json`) |
| `model` | string | 否 | (已废弃) 兼容旧字段，用于推断工作流 |

**请求示例**:

```json
{
  "url": "https://example.com/image.jpg",
  "type": "image",
  "workflow": "seedvr2_image_4096.json"
}
```

**响应示例**:

```json
{
  "status": "ok",
  "task_id": "f692edeb41cb4a3eaebd2db0044c0778"
}
```

---

### 2. 查询任务状态

获取指定任务的详细状态、进度和结果。

- **URL**: `/tasks/{task_id}`
- **Method**: `GET`

**响应参数**:

| 字段 | 类型 | 描述 |
|------|------|------|
| `task_id` | string | 任务唯一标识 |
| `status` | string | 任务状态 (`pending`, `processing`, `completed`, `failed`, `canceled`) |
| `stages` | array | 任务阶段详情（下载、处理、上传） |
| `output` | object | 任务结果，包含 `url` 和 `size_mb` |
| `error` | string | 如果失败，显示错误信息 |
| `created_at` | string | 创建时间 (UTC) |

**响应示例**:

```json
{
  "task_id": "f692edeb41cb4a3eaebd2db0044c0778",
  "status": "completed",
  "created_at": "2026-01-02T14:14:34.789595Z",
  "stages": [
    {
      "name": "download",
      "status": "success",
      "duration": 0.1,
      "detail": "Download complete"
    },
    {
      "name": "process",
      "status": "success",
      "duration": 52.17,
      "detail": "Processing complete"
    },
    {
      "name": "upload",
      "status": "success",
      "duration": 15.88,
      "detail": "Upload complete"
    }
  ],
  "output": {
    "url": "https://bucket.oss-region.aliyuncs.com/outputs/xxx/result.png",
    "size_mb": 13.38
  }
}
```

---

### 3. 取消任务

取消一个正在运行或排队中的任务。

- **URL**: `/tasks/{task_id}`
- **Method**: `DELETE`

**响应示例**:

```json
{
  "status": "canceled"
}
```

---

### 4. 系统监控

获取系统整体状态和服务器池信息。

- **URL**: `/monitor/stats`
- **Method**: `GET`

**响应示例**:

```json
{
  "system": {
    "max_workers": 1,
    "active_workers": 0,
    "queue_size": 0
  },
  "pool_status": [
    {
      "address": "http://127.0.0.1:8188",
      "status": "idle",
      "last_active": 1767363327.06
    }
  ],
  "stats": {
    "pending": 0,
    "processing": 0,
    "completed": 10,
    "failed": 2
  }
}
```

### 5. 健康检查

- **URL**: `/health`
- **Method**: `GET`

**响应**: `{"status": "ok"}`
