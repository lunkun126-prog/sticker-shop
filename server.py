# -*- coding: utf-8 -*-
"""贴纸美容小铺 本地服务：提供游戏页面 + 真人感语音（微软神经网络语音 edge-tts，生成过的句子缓存到 %LOCALAPPDATA%/StickerShop/tts_cache）。
由「启动贴纸美容小铺.bat」拉起；端口已被占用（服务已经在跑）时直接退出。"""
import asyncio, hashlib, os, sys, threading, time, urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.environ.get("LOCALAPPDATA", HERE), "StickerShop", "tts_cache")  # 不放 OneDrive，免得同步一堆小文件
PORT = 8765
VOICES = {  # 游戏里只用这几个，防止被拿去随便调
    "narrator": "zh-CN-XiaoxiaoNeural",
    "girl": "zh-CN-XiaoyiNeural",
    "boy": "zh-CN-YunxiaNeural",
    "en": "en-US-AnaNeural",
}
_locks = {}
_last = [time.time()]
IDLE_EXIT = 2 * 3600  # 两小时没人玩就自己退出
_locks_guard = threading.Lock()


def synth(text, voice_key):
    import edge_tts
    voice = VOICES[voice_key]
    key = hashlib.sha1(f"{voice}|{text}".encode("utf-8")).hexdigest()
    path = os.path.join(CACHE, key + ".mp3")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    with _locks_guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        if not os.path.exists(path):
            os.makedirs(CACHE, exist_ok=True)
            tmp = path + ".part"
            rate = "-8%" if voice_key == "en" else "+0%"
            asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(tmp))
            os.replace(tmp, path)
    return path


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, *a):
        pass

    def do_GET(self):
        _last[0] = time.time()
        u = urllib.parse.urlparse(self.path)
        if u.path != "/tts":
            return super().do_GET()
        q = urllib.parse.parse_qs(u.query)
        text = (q.get("t") or [""])[0].strip()[:200]
        voice = (q.get("v") or ["narrator"])[0]
        if not text or voice not in VOICES:
            self.send_error(400)
            return
        try:
            data = open(synth(text, voice), "rb").read()
        except Exception as e:  # 没网或服务不通：让前端退回系统朗读
            self.send_error(503, str(e)[:100])
            return
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=31536000")
        self.end_headers()
        self.wfile.write(data)


def already_running():
    """Windows 上 HTTPServer 默认开 SO_REUSEADDR，重复 bind 同端口照样成功，只能 connect 探测。"""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
            return True
    except OSError:
        return False


if __name__ == "__main__":
    if already_running():
        sys.exit(0)  # 桌面图标和 launchpad 起的是同一个服务，已在跑就不再叠一个
    ThreadingHTTPServer.allow_reuse_address = False
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        sys.exit(0)
    def idle_watch():
        while time.time() - _last[0] < IDLE_EXIT:
            time.sleep(60)
        os._exit(0)
    threading.Thread(target=idle_watch, daemon=True).start()
    srv.serve_forever()
