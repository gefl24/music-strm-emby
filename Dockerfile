# 🟢 关键修改：升级到 Python 3.12 (该库的最低要求)
FROM python:3.12-bookworm

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装基础编译工具 (防止依赖库缺少 Wheel 包时编译失败)
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

# 安装依赖
# python-115: 核心库
# flask, requests: Web服务库
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
