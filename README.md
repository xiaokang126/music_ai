# 失恋广场 💔🎵

一个以音乐为情感纽带的网页社区平台。学习乐理、AI 辅助创作音乐、在广场中用旋律与他人对话。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite 5 + TailwindCSS + Tone.js + recharts |
| 后端 | Python FastAPI + SQLAlchemy + SQLite |
| AI | DeepSeek API (deepseek-chat) |

## 快速启动

### 1. 后端

```bash
cd backend

# 使用已有 conda 环境
conda activate musicai

# 或创建新的虚拟环境
# conda create -n musicai python=3.11 -y
# conda activate musicai
# pip install -r requirements.txt

# 初始化数据库（首次运行）
python init_db.py

# 启动后端（监听 0.0.0.0:8000）
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`，自动代理 `/api` 到后端 `8000` 端口。

### 3. 外部访问

前端和后端都绑定在 `0.0.0.0`，局域网或公网可直接通过 IP + 端口访问。

## 功能模块

- 📖 **乐理课堂** — 音阶、和弦、节奏、情绪映射四章教程，交互式试听
- 🎼 **AI 创作** — 输入情绪文字 → DeepSeek 转音乐参数 → Tone.js 浏览器合成
- 🏛️ **音乐广场** — 发布/浏览作品，点赞评论，情绪标签筛选
- 💬 **音乐对话** — 用一段旋律回复他人的作品
- ✨ **情绪共鸣** — AI 匹配情绪频率相近的陌生人作品
- 📝 **情绪日记** — recharts 可视化情绪成长曲线
- 🌱 **治愈计划** — 7/14/30 天结构化疗愈任务
- 🎁 **虚拟礼物** — 赠送花束/暖灯/星光等温暖礼物
- 👤 **个人主页** — 作品管理、收藏、治愈进度

## 项目结构

```
music_ai/
├── frontend/          # React 前端
├── backend/           # Python FastAPI 后端
│   ├── .env           # API Key 等配置
│   └── app/
│       ├── models/    # 数据模型
│       ├── schemas/   # Pydantic 校验
│       ├── routers/   # API 路由
│       └── services/  # 业务逻辑
├── plan.md            # 详细方案文档
└── README.md
```

## 环境变量

后端 `.env` 文件配置：

```
DEEPSEEK_API_KEY=sk-7010e5b6517c485886b3422c6b6cc6c3
JWT_SECRET=your_secret_here
DATABASE_URL=sqlite:///./music_ai.db
```
