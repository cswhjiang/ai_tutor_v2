```bash
uv sync --python 3.12
source .venv/bin/activate
python --version
```

* 运行后端

本地开发环境使用：

```bash
bash server/start_service_dev.sh
```

等价命令：

```bash
export DOMAIN="http://localhost"
python -m uvicorn server.main:app --port 9501 --host 0.0.0.0
```

生产/多 worker 环境使用：

```bash
bash server/start_service.sh
```

启动后访问：

```text
http://localhost:9501/docs
```

* 验证环境

```bash
python -m pytest test_adk -q
python -m pip check
```

* 运行cli前端

```bash
python apps/art_cli.py --message {your_message}
```

* 运行web前端

先启动后端：

```bash
source .venv/bin/activate
bash server/start_service_dev.sh
```

再开第二个终端启动前端：

```bash
cd web
npm install
npm run dev
```

访问：

```text
http://localhost:5173
```

如果后端不是本机 `9501` 端口，可以在启动前端前指定：

```bash
VITE_API_BASE_URL=http://localhost:9501 npm run dev
```

前端配置示例见：

```text
web/.env.example
```

* 用样例题运行一次系统

先启动后端，保持这个终端不要关闭：

```bash
source .venv/bin/activate
bash server/start_service_dev.sh
```

再开第二个终端，运行 CLI 前端并发送题目：

```bash
source .venv/bin/activate
python apps/art_cli.py --message "What is the percentage increase in the area of a triangle if the height of the triangle is decreased by 10% and its base is increased by 20%?"
```

运行时 CLI 会先请求后端创建 session，然后把题目发送到 `/chat` 接口，并持续打印后端返回的流式执行过程和最终回答。

这道题的计算思路是：三角形面积与 `base * height` 成正比。高度变为原来的 `90%`，底边变为原来的 `120%`，所以新面积比例是 `0.9 * 1.2 = 1.08`，面积增加 `8%`。
