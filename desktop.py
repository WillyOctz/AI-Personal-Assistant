import argparse
import threading
import ctypes
import json
import logging
import os
import socket
import sys
import time
import urllib.request
from ctypes import wintypes
from logging.handlers import RotatingFileHandler
from pathlib import Path


#-------ENVIRONMENT----------
ROOT = (
    Path(sys.executable).parent if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from assistant import autostart, events, memory, notifier

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
APPDATA = Path(os.getenv("APPDATA", str(ROOT))) / "Nebula"
APPDATA.mkdir(parents=True, exist_ok=True)
RUNTIME_FILE = APPDATA / "runtime.json"

logging.basicConfig(
    level=logging.INFO,
    handlers=[RotatingFileHandler(
        LOG_DIR / "nebula.log", maxBytes=1_000_000,
        backupCount=3, encoding="utf-8"
    )],
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
log = logging.getLogger("nebula.desktop")

import keyboard
import pystray
import uvicorn
import webview
from PIL import Image, ImageDraw

from assistant.guard import SESSION_TOKEN, make_guard
from assistant.runtime import hooks, ui_state

HOTKEY = "ctrl+alt+space"
WIN_W, WIN_H = 420, 680

window = None
tray_icon = None
server = None
quitting = False
_last_tray_state = None


#--------------SINGLE INSTANCE---------------------
_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\NebulaAssistantSingleton")
ALREADY_RUNNING = ctypes.windll.kernel32.GetLastError() == 183

def signal_running_instance():
    try:
        info = json.loads(RUNTIME_FILE.read_text(encoding="utf-8"))
        request = urllib.request.Request(
            f"http://127.0.0.1:{info['port']}/__control/show",
            method="POST",
            headers={"x-nebula-token": info["token"]}
        )
        urllib.request.urlopen(request, timeout=2)
    except Exception:
        log.exception("Could not signal running instance")
        
        
#--------------------------------SERVER------------------------------
def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    
def wait_for_server(server, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if server.started:
            return True
        time.sleep(0.1)
    return False


#-------------------------WINDOW HELPERS--------------------------------
def place_window():
    rect = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
    window.move(rect.right - WIN_W - 16, rect.bottom - WIN_H - 16)
    
    
def show_window():
    window.show()
    window.restore()
    place_window()
    ui_state["visible"] = True
    try:
        window.evaluate_js("document.getElementById('message-input')?.focus()")
    except Exception:
        pass
    
    
def hide_window():
    window.hide()
    ui_state["visible"] = False
    

def toggle_window():
    hide_window() if ui_state["visible"] else show_window()
    
class JsApi:
    def hide(self):
        hide_window()
        
def on_closing():
    if quitting:
        return True
    hide_window()
    return False


#------------------------------------------TRAY----------------------------
def make_icon(color="#7c5cff", size=64):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((6, 6, size - 6, size - 6), fill=color)
    draw.ellipse((18, 16, 34, 32), fill=(255, 255, 255, 110))
    return image


def quit_app(icon=None, item=None):
    global quitting
    quitting = True
    try:
        keyboard.unhook_all()
    except Exception:
        pass
    if tray_icon:
        tray_icon.stop()
    if server:
        server.should_exit = True
    notifier.stop()
    window.destroy()
    
def tick():
    global _last_tray_state
    from assistant import focus
    active = bool(focus.get_focus_mode())
    paused = bool(memory.get_setting("notifications_paused", False))
    state = (active, paused)
    if tray_icon and state != _last_tray_state:
        color = "#5beb7a" if active else ("#6b6f85" if paused else "#f74b4b")
        tray_icon.icon = make_icon(color)
        tray_icon.title = "Nebula - focusing" if active else ("Nebula - paused" if paused else "Nebula")
        _last_tray_state = state
        
def toggle_autostart(icon, item):
    autostart.disable() if autostart.is_enabled() else autostart.enable()
    icon.update_menu()
    
def toggle_pause(icon ,item):
    memory.set_setting("notifications_paused",not memory.get_setting("notifications_paused", False))
    tick()
    icon.update_menu()

def set_verbosity(level):
    def _set(icon, item):
        memory.set_setting("verbosity", level)
        icon.update_menu()
    return _set

def verbosity_is(level):
    return lambda item: memory.get_setting("verbosity", "normal") == level

def open_dev_console(icon=None, item=None):
    show_window()
    window.evaluate_js("window.location.href = '/dev'")
    
def build_tray():
    global tray_icon
    tray_icon = pystray.Icon(
        "nebula", make_icon(), "Nebula",
        menu=pystray.Menu(
            pystray.MenuItem("Show / Hide", lambda icon, item: toggle_window(), default=True),
            pystray.MenuItem("Voice", pystray.Menu(
                pystray.MenuItem("Minimal", set_verbosity("minimal"), checked=verbosity_is("minimal"), radio=True),
                pystray.MenuItem("Normal", set_verbosity("normal"), checked=verbosity_is("normal"), radio=True),
                pystray.MenuItem("Chatty", set_verbosity("chatty"), checked=verbosity_is("chatty"), radio=True),
            )),
            pystray.MenuItem("Pause notifications", toggle_pause,
                             checked=lambda item: memory.get_setting("notifications_paused", False)),
            pystray.MenuItem("Start with Windows", toggle_autostart,
                             checked=lambda item: autostart.is_enabled()),
            pystray.MenuItem("Dev console", open_dev_console),
            pystray.MenuItem("Open logs folder", lambda icon, item: os.startfile(LOG_DIR)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Nebula", quit_app),
        ),
    )
    tray_icon.run_detached()
     
#---------------------------MAIN------------------------------------
def main():
    global window, server
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--background", action="store_true", help="tart hidden in tray")
    parser.add_argument("--debug", action="store_true", help="open WebView dev tools")
    args = parser.parse_args()
    
    if ALREADY_RUNNING:
        signal_running_instance()
        return 
    
    from api import app as fastapi_app
    
    port = free_port()
    fastapi_app.add_middleware(make_guard(port))
    
    config = uvicorn.Config(
        fastapi_app,
        host="127.0.0.1",
        port=port,
        log_config=None,        # logged manually
        access_log=False,
        timeout_graceful_shutdown=2,
    )
    
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True, name="uvicorn").start()
    
    if not wait_for_server(server):
        log.error("Server did not start within 20 seconds")
        return 
    
    RUNTIME_FILE.write_text(
        json.dumps({"port": port, "token": SESSION_TOKEN, "pid": os.getpid()}),
        encoding="utf-8",
    )
    
    hooks.update(show=show_window, hide=hide_window, toggle=toggle_window, tick=tick)
    ui_state["visible"] = not args.background
    
    notifier.start()
    
    window = webview.create_window(
        "Nebula",
        f"http://127.0.0.1:{port}/?token={SESSION_TOKEN}",
        width=WIN_W,
        height=WIN_H,
        on_top=True,                 
        hidden=args.background,
        js_api=JsApi(),
    )
    window.events.closing += on_closing
    
    build_tray()
    
    try:
        keyboard.add_hotkey(HOTKEY, toggle_window)
    except Exception:
        log.exception("Could not register hotkey")
        
    webview.start(place_window, debug=args.debug)
    
    #-----CLEANUP-----
    try:
        RUNTIME_FILE.unlink(missing_ok=True)
    except Exception:
        log.exception("Could not remove runtime file")
        
    time.sleep(0.3)
    os._exit(0)
    
if __name__ == "__main__":
    main()
