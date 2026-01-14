# Watch Together 

实时视频同步观看应用，支持多人在线同步播放视频，集成夸克网盘和AI服务。

## 功能特性

- 实时视频同步播放控制（播放/暂停/进度）
- 支持普通视频和M3U8流媒体
- 多人房间功能，支持房主和观众角色
- 集成夸克网盘API，支持网盘视频播放
- 内置DeepSeek AI对话助手
- WebSocket实时通信
- 视频流代理服务

## 技术栈

- **后端框架**: Flask + Flask-SocketIO
- **异步处理**: gevent
- **实时通信**: WebSocket
- **AI服务**: DeepSeek-V3.2 (ModelScope)
- **网盘集成**: QuarkPan

## 安装

### 环境要求

- Python 3.8+
- pip

### 安装步骤

1. 克隆项目
```bash
git clone <repository_url>
cd watch_together_bete
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法

### 启动服务

```bash
python app.py
```

服务默认运行在 `http://localhost:5000`

### 房主操作

1. 打开浏览器访问 `http://localhost:5000`
2. 输入昵称和房主密码（默认: 123）
3. 输入视频URL或选择夸克网盘视频
4. 开始播放，所有观众将同步观看

### 观众操作

1. 打开浏览器访问 `http://localhost:5000`
2. 输入昵称（无需密码）
3. 自动同步房主的播放状态

## 配置

### 修改房主密码

编辑 `app.py` 中的 `HOST_PASSWORD` 变量：

```python
HOST_PASSWORD = "your_password"
```

### 配置DeepSeek API

编辑 `app.py` 中的 `DEEPSEEK_API_KEY`：

```python
DEEPSEEK_API_KEY = "your_api_key"
```

## 项目结构

```
watch_together_bete/
├── app.py              # 主应用文件
├── index.html          # 前端页面
├── requirements.txt    # Python依赖
├── config/             # 配置文件目录
│   ├── login_result.json
│   └── user_info.json
└── QuarkPan/          # 夸克网盘客户端
    └── quark_client/
```

## API端点

- `GET /` - 主页面
- `GET /proxy` - 视频代理
- `GET /proxy_m3u8_ts` - M3U8 TS片段代理
- `GET /m3u8_playlist` - M3U8播放列表生成

## WebSocket事件

- `connect` - 客户端连接
- `disconnect` - 客户端断开
- `join_room` - 加入房间
- `video_update` - 视频状态更新
- `play` - 播放
- `pause` - 暂停
- `seek` - 跳转进度
- `chat_message` - 聊天消息
- `ai_chat` - AI对话

## 注意事项

- 确保网络连接稳定
- 视频URL需要支持跨域访问
- 夸克网盘视频需要有效的Cookie
- AI功能需要有效的API密钥


