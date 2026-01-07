# 🔴 关键修改：使用 python:3.9-bullseye (完整版)
# 这是一个基于 Debian 的完整系统，内置 GCC、Rust、OpenSSL 等所有编译环境
# 虽然体积较大，但能保证 100% 构建成功
FROM python:3.9-bullseye

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 复制依赖文件
COPY requirements.txt .

# 🔴 安装依赖
# 这里不需要再手动安装 gcc 了，直接安装 python 库
# 增加 --default-timeout 防止网络波动导致报错
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# 复制核心代码
COPY app.py .

# 创建输出目录
RUN mkdir -p /output

# 暴露端口
EXPOSE 8000

# 启动
CMD ["python", "app.py"]
