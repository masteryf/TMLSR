# TMLSR - 视频/图像超分服务

TMLSR 是一个基于 ComfyUI 的中间件服务，旨在提供高性能、可扩展的视频和图像超分辨率处理能力。它通过 RESTful API 管理任务队列，自动在多个 ComfyUI 服务器之间进行负载均衡，并将处理结果自动上传至阿里云 OSS。

## ✨ 核心特性

- **任务管理**：支持任务排队、状态追踪、自动重试和并发控制。
- **负载均衡**：动态检测 ComfyUI 服务器状态，智能分发任务（并发数 = 可用服务器数量）。
- **文件处理**：
  - 自动下载输入文件（支持自定义 User-Agent 以绕过防爬限制）。
  - 自动处理 ComfyUI 工作流中的文件上传和路径映射。
  - 处理完成后自动将结果上传至阿里云 OSS 并生成访问链接。
- **可视化监控**：内置 Web 仪表盘，实时监控系统状态、任务进度和服务器负载。
- **灵活扩展**：通过配置文件轻松添加或移除 ComfyUI 节点。

## 🛠️ 环境要求

- Python 3.8+
- 至少一个运行中的 ComfyUI 服务器（支持 API 模式）
- 阿里云 OSS 账号（用于存储输出文件）

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```
*(注：如果没有 requirements.txt，请确保安装 fastapi, uvicorn, requests, pyyaml, oss2, pydantic)*

### 2. 配置文件

在项目根目录下创建或修改 `config.yaml`：

```yaml
oss:
  endpoint: "oss-cn-hongkong.aliyuncs.com"
  access_key_id: "your_access_key_id"
  access_key_secret: "your_access_key_secret"
  bucket_name: "your_bucket_name"

server:
  max_retries: 3    # 任务失败重试次数
  retry_delay: 5    # 重试间隔（秒）

comfyui:
  servers:
    - "http://127.0.0.1:8188"
    - "https://your-remote-comfyui-server.com"
```

### 3. 启动服务

```bash
python3 start_server.py
```

服务默认运行在 `http://0.0.0.0:6008`。

### 4. 访问仪表盘

浏览器打开 `http://localhost:6008/dashboard` 即可查看实时任务监控面板。

## 📂 项目结构

```
TMLSR/
├── config.yaml          # 配置文件
├── start_server.py      # 启动脚本
├── server/              # 服务端核心代码
│   ├── main.py          # FastAPI 路由定义
│   ├── task_manager.py  # 任务管理与调度逻辑
│   ├── models.py        # 数据模型定义
│   └── static/          # 前端仪表盘资源
├── utils/               # 工具类
│   ├── comfy_utils.py   # ComfyUI API 交互
│   ├── comfy_pool.py    # 服务器池与负载均衡
│   └── oss_handler.py   # OSS 上传处理
├── workflows/           # ComfyUI 工作流 JSON 文件
└── test/                # 测试脚本
```

## 📝 API 文档

详细 API 文档请参考 [API.md](API.md)。

## 🧪 测试

使用提供的测试脚本验证服务是否正常运行：

```bash
# 测试图像超分
python3 test/test_image_seedvr2.py

# 测试视频超分
python3 test/test_video.py
```
