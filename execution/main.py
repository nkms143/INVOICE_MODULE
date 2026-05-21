import sys
import os
import uvicorn
import webbrowser
import threading
import time
import signal

# Fix for uvicorn logging error in PyInstaller
if getattr(sys, 'frozen', False):
    if sys.stdin is None:
        sys.stdin = open(os.devnull, "r")
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

# Determine paths
if getattr(sys, 'frozen', False):
    BASE_PATH = os.path.dirname(sys.executable)
    DATA_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    DATA_PATH = os.path.dirname(BASE_PATH)

sys.path.append(os.path.join(DATA_PATH, "execution"))

from app_backend import app, LAST_HEARTBEAT

def open_browser():
    """Waits for the server to start and then opens the default web browser."""
    time.sleep(2)
    print("[*] Launching browser at http://127.0.0.1:8000 ...")
    webbrowser.open("http://127.0.0.1:8000")

def monitor_heartbeat(server: uvicorn.Server):
    """Checks the last heartbeat time and shuts down if inactive."""
    import app_backend
    while not server.should_exit:
        time.sleep(10)
        # Check if browser was closed (no heartbeat for 30s)
        if time.time() - app_backend.LAST_HEARTBEAT > 30:
            print("[!] No heartbeat detected for 30 seconds. Shutting down gracefully...")
            server.should_exit = True
            break

if __name__ == "__main__":
    print("=" * 50)
    print("      GST INVOICE SYSTEM - STARTING UP      ")
    print("=" * 50)

    # Configure logging
    log_config = None if getattr(sys, 'frozen', False) else "logging.json"
    if not os.path.exists("logging.json") and not getattr(sys, 'frozen', False):
        log_config = None

    import socket
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    if is_port_in_use(8000):
        print("[*] GST Invoice System is already running. Opening existing session...")
        webbrowser.open("http://127.0.0.1:8000")
        sys.exit(0)

    # Create uvicorn server instance
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_config=log_config)
    server = uvicorn.Server(config)

    # Start background threads
    threading.Thread(target=open_browser, daemon=True).start()
    threading.Thread(target=monitor_heartbeat, args=(server,), daemon=True).start()

    # Handle signals for clean shutdown
    def handle_signal(sig, frame):
        print(f"[!] Received signal {sig}. Shutting down gracefully...")
        server.should_exit = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        server.run()
    except Exception as e:
        print(f"[-] Error starting server: {e}")
        input("Press Enter to exit...")
