# 🟢 必须使用 3.12 (python-115 的硬性要求)
FROM python:3.12-bookworm

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装编译依赖
# 这一步非常重要，保留它以确保底层库能编译通过
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

# 🟢 核心修正：
# 1. 环境已是 3.12 -> 解决了 versions: none 问题
# 2. 包名改回 python-115 -> 解决了 No matching distribution 问题
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
