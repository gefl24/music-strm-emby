# 使用 Python 3.10 官方镜像 (稳定，兼容性好)
FROM python:3.10

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 🔴 关键修改：直接安装库，不再读取 requirements.txt
# 这样可以彻底避免 Windows 换行符(\r\n) 导致的解析错误
# 同时加上 --verbose 以便如果再次出错能看到具体原因
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --verbose \
    flask \
    requests \
    p115

# 复制核心代码
COPY app.py .

# 创建输出目录
RUN mkdir -p /output

# 暴露端口
EXPOSE 8000

# 启动
CMD ["python", "app.py"]
