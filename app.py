import os
import json
import threading
import time
import requests
import logging
from urllib.parse import quote
from flask import Flask, redirect, request, render_template_string
from p115client import P115Client

# ================= 路径配置 =================
CONFIG_DIR = "/config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DATA_DIR = "/data"

# ================= 默认配置 =================
DEFAULT_CONFIG = {
    "cookie": os.environ.get("P115_COOKIE", ""),
    "host_url": os.environ.get("HOST_URL", "http://127.0.0.1:8777").rstrip('/'),
    "source_dir": os.environ.get("SOURCE_DIR", "/Music"),
    "scan_interval": int(os.environ.get("SCAN_INTERVAL", 3600))
}

current_config = DEFAULT_CONFIG.copy()
client = None
lock = threading.Lock()

# HTML 模板
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
        .path-info { background: #eee; padding: 10px; font-size: 0.9rem; border-radius: 4px; margin-bottom: 20px;}
    </style>
</head>
<body>
    <h2>⚙️ 115 Strm 服务设置 (WAF修复版)</h2>
    <div class="path-info">
        配置文件: {{ config_path }}<br>
        输出目录: {{ data_path }}
    </div>
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
            <input type="text" name="host_url" value="{{ config.host_url }}" required placeholder="http://192.168.XX.XX:8777">
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

def ensure_directories():
    if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR, exist_ok=True)

def load_config():
    global current_config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                current_config.update(json.load(f))
            logger.info(f"Loaded config from {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    else:
        logger.info("Using default config (env vars)")

def save_config(new_config):
    global current_config
    try:
        ensure_directories()
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=4)
        current_config = new_config
        logger.info("Config saved.")
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def login_115():
    global client
    cookie = current_config.get("cookie")
    if not cookie: return False

    # 1. 循环外初始化 client (关键修正：避免重试时丢失 Session Cookie)
    temp_client = None
    try:
        try:
            temp_client = P115Client(cookie, app="web")
        except TypeError:
            temp_client = P115Client(cookies=cookie, app="web")
        
        # 设置伪装 Header
        fake_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Referer": "https://115.com/",
            "Origin": "https://115.com",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive"
        }
        temp_client.headers.update(fake_headers)
    except Exception as e:
        logger.error(f"Client Init Failed: {e}")
        return False

    # 2. 循环重试验证 (复用同一个 temp_client)
    for attempt in range(3):
        try:
            # 发送测试请求
            temp_client.fs_files({"limit": 1})
            
            # 成功！赋值给全局 client
            client = temp_client
            logger.info("115 Login Successful (Passed WAF)")
            return True
            
        except Exception as e:
            if "405" in str(e):
                logger.warning(f"WAF Challenge triggered (Attempt {attempt+1}/3). Retrying in 3s...")
                # 405 响应会包含 Set-Cookie，Requests Session 会自动处理
                # 我们只需要等待几秒，用同一个 client 再次发起请求即可
                time.sleep(3)
                continue 
            else:
                logger.error(f"Login Verify Failed: {e}")
                # 如果是其他错误(如Cookie无效)，重试可能无用，但多试一次无妨
                time.sleep(1)
    
    logger.error("Failed to pass WAF after 3 attempts.")
    return False

def download_image(pickcode, filename, local_dir):
    local_path = os.path.join(local_dir, filename)
    if os.path.exists(local_path): return
    
    try:
        url = client.download_url(pickcode)
        r = client.session.get(url, stream=True, timeout=30)
        if r.status_code == 200:
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(1024*1024):
                    f.write(chunk)
            logger.info(f"Downloaded Image: {filename}")
    except Exception as e:
        logger.error(f"Error downloading image {filename}: {e}")

def walk_115(cid=0):
    """递归遍历 115 目录"""
    try:
        offset = 0
        limit = 1000 
        while True:
            resp = None
            # 每个 API 请求也增加简单的重试
            for retry in range(3):
                try:
                    resp = client.fs_files({"cid": cid, "offset": offset, "limit": limit})
                    break
                except Exception as e:
                    if "405" in str(e):
                        logger.warning(f"WAF in walk at {cid}, retrying...")
                        time.sleep(2)
                        continue
                    else:
                        logger.error(f"API Error: {e}")
                        break
            
            if not resp or not isinstance(resp, dict):
                break
                
            data = resp.get("data", [])
            if not data: break

            for item in data:
                yield item
                if "fid" in item: 
                    yield from walk_115(item["cid"])
            
            if len(data) < limit: break
            offset += limit
    except Exception as e:
        logger.error(f"Walk error at cid {cid}: {e}")

def create_nfo(filename, local_dir, album_name="Unknown", artist_name="Unknown"):
    nfo_name = os.path.splitext(filename)[0] + ".nfo"
    nfo_path = os.path.join(local_dir, nfo_name)
    if os.path.exists(nfo_path): return
    title = os.path.splitext(filename)[0]
    xml_content = f"""<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<musicvideo><title>{title}</title><artist>{artist_name}</artist><album>{album_name}</album><plot>Generated by 115-Strm-Service</plot></musicvideo>"""
    try:
        with open(nfo_path, 'w', encoding='utf-8') as f: f.write(xml_content)
    except: pass

def scanner_task():
    global client
    while True:
        with lock:
            target_path = current_config["source_dir"]
            interval = int(current_config["scan_interval"])
            host_url = current_config["host_url"].rstrip('/')
        
        if client is None:
            if not login_115():
                time.sleep(30)
                continue

        logger.info(f"--- Starting Scan: {target_path} ---")
        try:
            count = 0
            for item in walk_115(0): 
                if "fid" in item: continue 
                
                fname = item.get("n", "") or item.get("name", "")
                if not fname: continue
                
                ext = os.path.splitext(fname)[1].lower()
                pickcode = item.get("pc", "") or item.get("pickcode", "")
                local_dir = DATA_DIR 
                
                if ext in IMAGE_EXTS:
                    download_image(pickcode, fname, local_dir)
                elif ext in MUSIC_EXTS:
                    strm_name = os.path.splitext(fname)[0] + ".strm"
                    strm_path = os.path.join(local_dir, strm_name)
                    safe_filename = quote(fname)
                    file_url = f"{host_url}/play/{pickcode}/{safe_filename}"
                    
                    if not os.path.exists(strm_path):
                        with open(strm_path, 'w', encoding='utf-8') as f: f.write(file_url)
                        logger.info(f"Generated: {strm_name}")
                        count += 1
                    
                    create_nfo(fname, local_dir)

            logger.info(f"--- Scan Finished (New: {count}) ---\n")
        except Exception as e:
            logger.error(f"Scan Error: {e}")
            with lock: client = None
        
        time.sleep(interval)

@app.route('/')
def index(): return redirect('/admin')

@app.route('/admin')
def admin_page():
    status = "✅ 运行中" if client else "⚠️ 未连接"
    return render_template_string(HTML_TEMPLATE, config=current_config, status=status, config_path=CONFIG_FILE, data_path=DATA_DIR)

@app.route('/admin/save', methods=['POST'])
def admin_save():
    global client
    new_config = {
        "cookie": request.form.get('cookie'),
        "host_url": request.form.get('host_url'),
        "source_dir": request.form.get('source_dir'),
        "scan_interval": int(request.form.get('scan_interval'))
    }
    with lock:
        save_config(new_config)
        client = None
    return render_template_string(HTML_TEMPLATE, config=new_config, status="⏳ 重连中...", message="配置已保存！", config_path=CONFIG_FILE, data_path=DATA_DIR)

@app.route('/play/<pickcode>/<filename>')
def play_redirect(pickcode, filename):
    global client
    try:
        if client is None: login_115()
        url = client.download_url(pickcode)
        return redirect(url, code=302)
    except Exception as e:
        logger.error(f"Get Link Error: {e}")
        login_115()
        return f"Error: {e}", 500

if __name__ == '__main__':
    ensure_directories()
    load_config()
    t = threading.Thread(target=scanner_task, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=8778)
