# 使用基于 Debian Bookworm 的 Python 3.11 镜像 (包含更多预编译库)
FROM python:3.11-bookworm

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 🔴 关键修复：安装底层编译依赖
# p115 依赖的库可能需要编译，预先安装这些 C 库能解决 99% 的构建错误
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

# 分步安装依赖 (方便排查具体是哪个包挂了)
RUN pip install --no-cache-dir flask requests

# 🔴 单独安装 p115，并使用国内源备用 (有时 Github 连接 PyPI 不稳)
# 如果这一步报错，请查看 Github Actions 日志的详细输出
RUN pip install --no-cache-dir --verbose p115

# 复制核心代码
COPY app.py .
# 创建输出目录
RUN mkdir -p /output

# 暴露端口
EXPOSE 8000

# 启动
CMD ["python", "app.py"]
