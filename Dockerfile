# 使用 Python 3.12 (兼容性最佳)
FROM python:3.12-bookworm

WORKDIR /app
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装 Git 和编译环境
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

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir flask requests

RUN pip install --no-cache-dir git+https://github.com/ChenyangGao/p115client.git

COPY app.py .

# 创建分离的目录
RUN mkdir -p /config /data

# 暴露端口 8778 (Web管理)
EXPOSE 8778

CMD ["python", "app.py"]
