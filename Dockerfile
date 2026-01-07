# 使用 Python 3.12 (满足 p115 的最低版本要求)
FROM python:3.12-bookworm

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装基础编译工具
# 这些库是 p115 底层依赖 (如 pycryptodomex) 编译所必须的
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    libffi-dev \
    libssl-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 升级 pip
RUN pip install --no-cache-dir --upgrade pip

# 🟢 修正：包名改回 p115
# 环境已经是 Python 3.12 且有了编译工具，这次 p115 一定能安装成功
RUN pip install --no-cache-dir --verbose \
    flask \
    requests \
    p115

# 复制核心代码
COPY app.py .

# 创建输出目录
RUN mkdir -p /output

# 暴露端口
EXPOSE 8000

# 启动
CMD ["python", "app.py"]
