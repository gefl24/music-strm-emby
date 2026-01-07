# 使用基于 Debian Bookworm 的 Python 3.11 镜像
FROM python:3.11-bookworm

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装底层编译依赖 (python-115 可能依赖其中的加解密库)
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

# 分步安装依赖
RUN pip install --no-cache-dir flask requests

# 🔴 关键修复：包名是 "python-115"，而不是 "p115"
RUN pip install --no-cache-dir --verbose python-115

# 复制核心代码
COPY app.py .

# 创建输出目录
RUN mkdir -p /output

# 暴露端口
EXPOSE 8000

# 启动
CMD ["python", "app.py"]
