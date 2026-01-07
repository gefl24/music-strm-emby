# 使用 Slim 版本作为基础，方便我们掌控环境
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 🔴 关键修复步骤 1：安装所有构建依赖
# build-essential: 提供 gcc 编译器
# libffi-dev, libssl-dev: 加密库通常需要的头文件
# python3-dev: 编译 Python 扩展所需的头文件
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 🔴 关键修复步骤 2：优化 pip 安装策略
# --upgrade pip wheel setuptools: 确保构建工具是最新的
# --prefer-binary: 告诉 pip 尽量找预编译包，不要轻易尝试从源码编译
# --no-cache-dir: 减小镜像体积
RUN pip install --upgrade pip wheel setuptools && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# 复制核心代码
COPY app.py .

# 创建输出目录
RUN mkdir -p /output

# 暴露端口
EXPOSE 8000

# 启动
CMD ["python", "app.py"]
