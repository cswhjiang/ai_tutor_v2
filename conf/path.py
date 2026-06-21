# coding: utf-8
# @author: zyh
# @file: path.py
import os

# 项目所在的绝对路径
PROJECT_PATH = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)  # 项目所在目录

CONF_ROOT = os.path.join(PROJECT_PATH, "conf")  # 配置文件所在目录
DATA_ROOT = os.path.join(PROJECT_PATH, "data")  # 数据文件所在目录
VAR_ROOT = os.path.join(PROJECT_PATH, "var")  # 本地运行产物所在目录
DATABASE_ROOT = os.path.join(VAR_ROOT, "database")  # 数据库文件所在目录
LOGS_ROOT = os.path.join(VAR_ROOT, "logs")  # 日志文件所在目录
OUTPUTS_ROOT = os.path.join(VAR_ROOT, "outputs")  # 生成结果所在目录
SRC_ROOT = os.path.join(PROJECT_PATH, "src")  # 源代码文件所在目录
TEST_ROOT = os.path.join(PROJECT_PATH, "tests")  # 测试文件所在目录
WEB_ROOT = os.path.join(PROJECT_PATH, "web")  # 前端文件所在目录
