# 必须使用 Python 3.12 (兼容性最佳)
FROM python:3.12-bookworm

WORKDIR /app
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装编译依赖和 git
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

# 从源码安装 p115
RUN pip install --no-cache-dir git+https://github.com/ChenyangGao/p115.git

COPY app.py .
RUN mkdir -p /output

# 🔴 暴露 8778 端口
EXPOSE 8778

CMD ["python", "app.py"]
