# 🟢 必须使用 Python 3.12 (满足 python-115 的硬性要求)
FROM python:3.12-bookworm

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装基础编译工具 (防止底层依赖编译失败)
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
# 1. 不使用清华源，直接走官方 PyPI (GitHub Actions 在海外，连官方源极快)
# 2. 包名使用 python-115
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
