# 使用官方 Python 轻量镜像
FROM python:3.11

# 设置工作目录
WORKDIR /app

# 设置时区为上海 (方便查看日志时间)
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 复制依赖并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制核心代码
COPY app.py .

# 创建输出挂载点
RUN mkdir -p /output

# 暴露端口
EXPOSE 8000

# 启动
CMD ["python", "app.py"]
