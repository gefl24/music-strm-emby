# 🔴 修改点1：去掉 -slim，使用完整版镜像，包含 gcc 等编译工具
FROM python:3.11

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
# 完整版镜像通常基于 Debian，配置时区方式略有不同，但通常此命令兼容
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 复制依赖并安装
COPY requirements.txt .
# 🔴 升级 pip 以确保能找到最新的 wheel 包
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制核心代码
COPY app.py .

# 创建输出目录
RUN mkdir -p /output

# 暴露端口
EXPOSE 8000

# 启动
CMD ["python", "app.py"]
