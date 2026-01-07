# 使用 Python 3.12 (兼容性最佳)
FROM python:3.12-bookworm

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 🔴 关键修改：加入 git，用于从源码安装库
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    libffi-dev \
    libssl-dev \
    zlib1g-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# 升级 pip
RUN pip install --no-cache-dir --upgrade pip

# 1. 先安装普通依赖
RUN pip install --no-cache-dir flask requests

# 🔴 2. 核心修正：直接从 GitHub 安装 p115
# 这能彻底解决 PyPI 上找不到包、包名不对、版本不匹配等所有问题
RUN pip install --no-cache-dir git+https://github.com/ChenyangGao/p115client.git

# 复制核心代码
COPY app.py .

# 创建输出目录
RUN mkdir -p /output

# 暴露端口
EXPOSE 8000

# 启动
CMD ["python", "app.py"]
