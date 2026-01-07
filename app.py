import os
import json
import threading
import time
import requests
import logging
from urllib.parse import quote
from flask import Flask, redirect, request, render_template_string
from p115 import P115FileSystem, P115Client

# ================= 全局配置管理 =================
CONFIG_FILE = "/output/config.json"  # 配置文件保存在映射目录，防止丢失

# 默认配置 (优先读取环境变量作为初始值)
DEFAULT_CONFIG = {
    "cookie": os.environ.get("P115_COOKIE", ""),
    "host_url": os.environ.get("HOST_URL", "http://127.0.0.1:8000").rstrip('/'),
    "source_dir": os.environ.get("SOURCE_DIR", "/Music"),
    "scan_interval": int(os.environ.get("SCAN_INTERVAL", 3600))
}

# 全局变量
current_config = DEFAULT_CONFIG.copy()
fs = None
lock = threading.Lock()

# 简单的 HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>115 Music Strm 管理</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 2rem auto; padding: 0 1rem; }
        .form-group { margin-bottom: 1rem; }
        label { display: block; margin-bottom: 0.5rem; font-weight: bold; }
        input { width: 100%; padding: 0.5rem; box-sizing: border-box; }
        button { background: #007bff; color: white; border: none; padding: 0.7rem 1.5rem; cursor: pointer; }
        button:hover { background: #0056b3; }
        .alert { padding: 1rem; margin-bottom: 1rem; border-radius: 4px; }
        .success { background-color: #d4edda; color: #155724; }
        .status { margin-bottom: 20px; padding: 10px; background: #f8f9fa; border-left: 5px solid #007bff; }
    </style>
</head>
<body>
    <h2>⚙️ 115 Strm 服务设置</h2>
    
    <div class="status">
        当前状态: <strong>{{ status }}</strong><br>
        扫描目标: {{ config.source_dir }}
    </div>

    {% if message %}
    <div class="alert success">{{ message }}</div>
    {% endif %}

    <form method="POST" action="/admin/save">
        <div class="form-group">
            <label>115 Cookie (UID; CID; SEID)</label>
            <input type="text" name="cookie" value="{{ config.cookie }}" required placeholder="UID=...;CID=...;SEID=...">
        </div>
        
        <div class="form-group">
            <label>本机局域网地址 (Host URL)</label>
            <input type="text" name="host_url" value="{{ config.host_url }}" required placeholder="http://192.168.XX.XX:8000">
            <small style="color:gray">Emby播放时会访问此地址，请确保填写真实IP</small>
        </div>

        <div class="form-group">
            <label>115 音乐目录 (Source Dir)</label>
            <input type="text" name="source_dir" value="{{ config.source_dir }}" required>
        </div>

        <div class="form-group">
            <label>扫描间隔 (秒)</label>
            <input type="number" name="scan_interval" value="{{ config.scan_interval }}" required>
        </div>

        <button type="submit">保存并应用</button>
    </form>
</body>
</html>
"""

IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.tbn')
MUSIC_EXTS = ('.mp3', '.flac', '.wav', '.m4a', '.dsf', '.dff', '.ape', '.wma', '.aac')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

def load_config():
    """加载配置：文件 > 环境变量"""
    global current_config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                # 合并配置，防止旧版本缺少字段
                current_config.update(saved_config)
            logger.info("Loaded config from file.")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    else:
        logger.info("No config file found, using defaults.")

def save_config(new_config):
    """保存配置到文件"""
    global current_config
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=4)
        current_config = new_config
        logger.info("Config saved.")
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def login_115():
    """初始化 115 连接"""
    global fs
    cookie = current_config.get("cookie")
    if not cookie:
        logger.warning("No Cookie set!")
        return False

    try:
        client = P115Client(cookie=cookie)
        fs = P115FileSystem(client)
        logger.info("115 Login Successful")
        return True
    except Exception as e:
        logger.error(f"Login Failed: {e}")
        return False

def sync_image(file_info, local_dir):
    filename = file_info['name']
    local_path = os.path.join(local_dir, filename)
    remote_size = int(file_info.get('size', 0))
    
    if os.path.exists(local_path):
        if os.path.getsize(local_path) == remote_size:
            return 
    
    logger.info(f"Downloading Image: {filename}")
    try:
        url = fs.get_url(file_info['pickcode'])
        r = requests.get(url, stream=True, timeout=30)
        if r.status_code == 200:
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(1024*1024):
                    f.write(chunk)
    except Exception as e:
        logger.error(f"Error downloading image {filename}: {e}")

def create_nfo(filename, local_dir, album_name="Unknown", artist_name="Unknown"):
    nfo_name = os.path.splitext(filename)[0] + ".nfo"
    nfo_path = os.path.join(local_dir, nfo_name)
    if os.path.exists(nfo_path): return

    title = os.path.splitext(filename)[0]
    xml_content = f"""<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<musicvideo>
  <title>{title}</title>
  <artist>{artist_name}</artist>
  <album>{album_name}</album>
  <plot>Generated by 115-Strm-Service</plot>
</musicvideo>"""
    try:
        with open(nfo_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
    except Exception as e:
        logger.error(f"Error creating NFO: {e}")

def scanner_task():
    while True:
        # 每次循环开始前，重新检查是否需要登录 (配置可能已变更)
        with lock:
            target_dir = current_config["source_dir"]
            interval = int(current_config["scan_interval"])
            host_url = current_config["host_url"].rstrip('/')
        
        if fs is None:
            if not login_115():
                time.sleep(30)
                continue

        logger.info(f"--- Starting Scan: {target_dir} ---")
        try:
            for root, dirs, files in fs.walk(target_dir):
                rel_path = os.path.relpath(root, target_dir)
                local_dir = "/output" if rel_path == "." else os.path.join("/output", rel_path)
                
                if not os.path.exists(local_dir):
                    os.makedirs(local_dir, exist_ok=True)

                album_name = os.path.basename(root)
                try:
                    artist_name = os.path.basename(os.path.dirname(root))
                except:
                    artist_name = "Unknown"

                for file in files:
                    fname = file['name']
                    ext = os.path.splitext(fname)[1].lower()

                    if ext in IMAGE_EXTS:
                        sync_image(file, local_dir)
                    elif ext in MUSIC_EXTS:
                        strm_name = os.path.splitext(fname)[0] + ".strm"
                        strm_path = os.path.join(local_dir, strm_name)
                        safe_filename = quote(fname)
                        
                        # 使用动态读取的 host_url
                        file_url = f"{host_url}/play/{file['pickcode']}/{safe_filename}"
                        
                        if not os.path.exists(strm_path):
                            with open(strm_path, 'w', encoding='utf-8') as f:
                                f.write(file_url)
                            logger.info(f"Generated: {strm_name}")
                        else:
                             # 检查 URL 是否变化 (例如用户在网页改了IP)
                            with open(strm_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            if content != file_url:
                                with open(strm_path, 'w', encoding='utf-8') as f:
                                    f.write(file_url)
                                logger.info(f"Updated URL: {strm_name}")

                        create_nfo(fname, local_dir, album_name, artist_name)
            
            logger.info("--- Scan Finished ---\n")
        except Exception as e:
            logger.error(f"Scan Error: {e}")
            # 出错重置 fs，触发下次循环重新登录
            with lock:
                global fs
                fs = None 

        time.sleep(interval)

# ================= Web 路由 =================

@app.route('/')
def index():
    return redirect('/admin')

@app.route('/admin')
def admin_page():
    status = "✅ 运行中" if fs else "⚠️ 未连接 (请检查Cookie)"
    return render_template_string(HTML_TEMPLATE, config=current_config, status=status)

@app.route('/admin/save', methods=['POST'])
def admin_save():
    global fs
    new_config = {
        "cookie": request.form.get('cookie'),
        "host_url": request.form.get('host_url'),
        "source_dir": request.form.get('source_dir'),
        "scan_interval": int(request.form.get('scan_interval'))
    }
    
    with lock:
        save_config(new_config)
        # 强制下线，触发扫描线程重新登录
        fs = None 
    
    return render_template_string(HTML_TEMPLATE, config=new_config, status="⏳ 正在重连...", message="配置已保存！正在重新连接 115...")

@app.route('/play/<pickcode>/<filename>')
def play_redirect(pickcode, filename):
    global fs
    try:
        if fs is None: login_115()
        url = fs.get_url(pickcode)
        return redirect(url, code=302)
    except Exception as e:
        logger.error(f"Get Link Error: {e}")
        # 尝试重登
        login_115()
        return f"Error: {e}", 500

if __name__ == '__main__':
    load_config() # 启动时加载配置
    t = threading.Thread(target=scanner_task, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=8000)
