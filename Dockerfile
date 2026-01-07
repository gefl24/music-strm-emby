# 🟢 1. 必须使用 Python 3.12 (该库的硬性要求)
FROM python:3.12-bookworm

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 2. 安装编译依赖
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

# 🟢 3. 核心修正：
# - 移除了清华源 (-i ...)，直接使用官方 PyPI
# - 官方源在 GitHub Actions 环境下 100% 能找到包
RUN pip install --no-cache-dir --verbose \
    flask \
    requests \
    python-115

# 复制核心代码
COPY app.py .

# 创建输出目录
RUN mkdir -p /output

# 暴露端口
EXPOSE 8000

# 启动
CMD ["python", "app.py"]
