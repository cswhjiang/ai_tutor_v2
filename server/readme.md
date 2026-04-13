服务代码架构如下
```txt
server/
├── main.py                # 应用入口：初始化 FastAPI、CORS 和路由挂载
├── database.py            # 数据库配置：引擎创建与 SessionLocal
├── models.py              # 数据库模型：SQLAlchemy 表定义
├── schemas.py             # 数据验证模型：Pydantic 类
├── agents_manager.py      # ADK相关：所有专家 Agent 与 Runner 的初始化
├── utils/                 # 工具类文件夹
│   ├── auth.py            # 权限工具：加密、JWT、Google OAuth 验证
│   ├── email.py           # 邮件工具：SMTP 异步发送
│   └── common.py          # 通用工具：文件保存、SSE 格式化、State 初始化
└── routers/                # 路由文件夹
    ├── chat.py            # 会话与工作流接口 (/chat, /session/create)
    ├── auth.py            # 用户认证接口 (注册、登录、验证码)
    ├── billing.py         # 支付接口 (Stripe 相关)
    └── user.py            # 用户管理接口 (个人信息、积分)
```