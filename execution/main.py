import sys
import os

# -------------------------------------------------------------
# Scheme Registration (Must happen BEFORE importing other QWebEngine classes
# and BEFORE QApplication is created)
# -------------------------------------------------------------
from PySide6.QtWebEngineCore import QWebEngineUrlScheme

SCHEME_NAME = b"app"
scheme = QWebEngineUrlScheme(SCHEME_NAME)
scheme.setSyntax(QWebEngineUrlScheme.Syntax.HostAndPort)
scheme.setFlags(
    QWebEngineUrlScheme.Flag.LocalScheme | 
    QWebEngineUrlScheme.Flag.SecureScheme | 
    QWebEngineUrlScheme.Flag.LocalAccessAllowed |
    QWebEngineUrlScheme.Flag.FetchApiAllowed |
    QWebEngineUrlScheme.Flag.CorsEnabled
)
QWebEngineUrlScheme.registerScheme(scheme)

# -------------------------------------------------------------
# Standard Imports
# -------------------------------------------------------------
import sqlite3
import tempfile
import uuid
from PySide6.QtCore import QByteArray, QIODevice, QBuffer, QUrl, QObject, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineUrlSchemeHandler, QWebEngineProfile, QWebEngineUrlRequestJob, QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PySide6.QtGui import QIcon, QDesktopServices
from fastapi.testclient import TestClient
import json
import base64

class LoggingWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, sourceId):
        # Print JS console message to terminal
        print(f"[JS Console] Level {level} | Line {line} in {sourceId}:\n  {message}", file=sys.stderr)


# Fix for uvicorn/standard output logging errors in PyInstaller
if getattr(sys, 'frozen', False):
    try:
        log_dir = os.path.join(os.path.expanduser("~"), "Documents", "GST_Invoice_System")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")
        log_fp = open(log_file, "a", encoding="utf-8", buffering=1)
        sys.stdout = log_fp
        sys.stderr = log_fp
        print("\n--- APP LOG STARTED ---", flush=True)
    except Exception:
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w")
    if sys.stdin is None:
        sys.stdin = open(os.devnull, "r")

# Determine paths
if getattr(sys, 'frozen', False):
    BASE_PATH = os.path.dirname(sys.executable)
    DATA_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    DATA_PATH = os.path.dirname(BASE_PATH)

sys.path.append(os.path.join(DATA_PATH, "execution"))

from app_backend import app, DB_PATH, UPLOADS_DIR

# -------------------------------------------------------------
# Custom Scheme Handler
# -------------------------------------------------------------
class FastAPIUrlSchemeHandler(QWebEngineUrlSchemeHandler):
    def __init__(self, fastapi_app):
        super().__init__()
        # Initialize TestClient to route requests in-memory without a network port
        self.client = TestClient(fastapi_app, raise_server_exceptions=False)

    def requestStarted(self, job: QWebEngineUrlRequestJob):
        url = job.requestUrl()
        path = url.path()
        if not path:
            path = "/"

        query = url.query()
        if query:
            path = f"{path}?{query}"

        method = job.requestMethod().data().decode('utf-8')

        # Map headers
        headers = {}
        for k, v in job.requestHeaders().items():
            headers[k.data().decode('utf-8')] = v.data().decode('utf-8')

        # Read POST/PUT body if present
        body_bytes = b""
        if method in ("POST", "PUT"):
            device = job.requestBody()
            if device:
                body_bytes = device.readAll().data()

        try:
            # Send the request to FastAPI inside the local process
            response = self.client.request(
                method=method,
                url=path,
                headers=headers,
                content=body_bytes,
                follow_redirects=True
            )

            content = response.content
            mime_type_str = response.headers.get("content-type", "application/octet-stream")
            # Strip charset/parameters (e.g., text/html; charset=utf-8 -> text/html)
            mime_type_clean = mime_type_str.split(";")[0].strip().encode('utf-8')

            # Create a QBuffer to store the response content.
            # Parent the buffer to the job object to prevent garbage collection crashes.
            buffer = QBuffer(job)
            buffer.setData(QByteArray(content))
            buffer.open(QIODevice.ReadOnly)

            # Prevent Python garbage collection of buffer and content data
            job.buffer_ref = buffer
            job.data_ref = content

            job.reply(mime_type_clean, buffer)

        except Exception as e:
            print(f"[-] Custom Scheme Request Error: {e}", file=sys.stderr)
            # Graceful error page fallback
            error_content = f"<h1>Internal Server Error</h1><p>{str(e)}</p>".encode('utf-8')
            buffer = QBuffer(job)
            buffer.setData(QByteArray(error_content))
            buffer.open(QIODevice.ReadOnly)
            job.buffer_ref = buffer
            job.reply(b"text/html", buffer)

# -------------------------------------------------------------
# Printing and PDF Generation Support (Helper & Handler)
# -------------------------------------------------------------
class PrintHandler(QObject):
    def __init__(self, page):
        super().__init__(page)
        self.page = page
        self.temp_pdf_path = ""
        self.page.pdfPrintingFinished.connect(self.on_pdf_printing_finished)
        
    def print_to_pdf(self):
        temp_dir = tempfile.gettempdir()
        self.temp_pdf_path = os.path.join(temp_dir, f"print_{os.getpid()}_{uuid.uuid4().hex[:8]}.pdf")
        self.page.printToPdf(self.temp_pdf_path)
        
    def on_pdf_printing_finished(self, file_path, success):
        if file_path == self.temp_pdf_path:
            if success:
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            else:
                print(f"[-] PDF printing failed for path: {file_path}", file=sys.stderr)
            # Remove reference from page to allow cleanup
            if hasattr(self.page, "_print_handler") and self.page._print_handler == self:
                self.page._print_handler = None

def handle_print_requested(page):
    handler = PrintHandler(page)
    # Store reference to prevent garbage collection during async print
    page._print_handler = handler
    handler.print_to_pdf()

# -------------------------------------------------------------
# File Download Handler (Invoice PDFs, DB Backups)
# -------------------------------------------------------------
def handle_download(download_item):
    default_name = download_item.suggestedFileName()
    active_win = QApplication.activeWindow()
    save_path, _ = QFileDialog.getSaveFileName(
        active_win,
        "Save File",
        default_name,
        "All Files (*)"
    )
    if save_path:
        download_item.setDownloadDirectory(os.path.dirname(save_path))
        download_item.setDownloadFileName(os.path.basename(save_path))
        download_item.accept()
    else:
        download_item.cancel()

# -------------------------------------------------------------
# WebChannel API Bridge
# -------------------------------------------------------------
class Backend(QObject):
    def __init__(self, fastapi_app):
        super().__init__()
        self.client = TestClient(fastapi_app, raise_server_exceptions=False)

    @Slot(str, str, str, str, result=str)
    def call_api(self, method, url, body, headers_json):
        try:
            # Parse headers
            headers = json.loads(headers_json) if headers_json else {}
            
            # Send the request to FastAPI inside the local process
            body_bytes = body.encode('utf-8') if isinstance(body, str) else body
            response = self.client.request(
                method=method,
                url=url,
                headers=headers,
                content=body_bytes,
                follow_redirects=True
            )
            
            # Base64 encode response content to avoid encoding/decoding errors of binary/special characters
            content_b64 = base64.b64encode(response.content).decode('utf-8')
            res_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": content_b64,
                "is_base64": True
            }
            return json.dumps(res_data)
        except Exception as e:
            print(f"[-] API Bridge Error: {e}", file=sys.stderr)
            err_data = {
                "status_code": 500,
                "headers": {},
                "content": base64.b64encode(str(e).encode('utf-8')).decode('utf-8'),
                "is_base64": True
            }
            return json.dumps(err_data)

    @Slot(str, str, str, result=str)
    def upload_favicon(self, profile_id, filename, base64_data):
        try:
            content = base64.b64decode(base64_data)
            files = {'file': (filename, content, 'image/png')}
            response = self.client.post(
                f"/api/profiles/{profile_id}/favicon",
                files=files
            )
            content_b64 = base64.b64encode(response.content).decode('utf-8')
            res_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": content_b64,
                "is_base64": True
            }
            return json.dumps(res_data)
        except Exception as e:
            print(f"[-] Favicon Upload Bridge Error: {e}", file=sys.stderr)
            err_data = {
                "status_code": 500,
                "headers": {},
                "content": base64.b64encode(str(e).encode('utf-8')).decode('utf-8'),
                "is_base64": True
            }
            return json.dumps(err_data)

    @Slot(str, str, result=str)
    def restore_backup(self, filename, base64_data):
        try:
            content = base64.b64decode(base64_data)
            files = {'file': (filename, content, 'application/zip')}
            response = self.client.post(
                "/api/restore",
                files=files
            )
            content_b64 = base64.b64encode(response.content).decode('utf-8')
            res_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": content_b64,
                "is_base64": True
            }
            return json.dumps(res_data)
        except Exception as e:
            print(f"[-] Restore Backup Bridge Error: {e}", file=sys.stderr)
            err_data = {
                "status_code": 500,
                "headers": {},
                "content": base64.b64encode(str(e).encode('utf-8')).decode('utf-8'),
                "is_base64": True
            }
            return json.dumps(err_data)

# -------------------------------------------------------------
# Custom Web View (Handles target="_blank" window.open requests)
# -------------------------------------------------------------
class CustomWebEngineView(QWebEngineView):
    def __init__(self, backend_obj, parent=None):
        super().__init__(parent)
        self.setPage(LoggingWebEnginePage(self))
        self.backend_obj = backend_obj
        
        # Setup WebChannel for this page
        self.channel = QWebChannel(self)
        self.channel.registerObject("backend", self.backend_obj)
        self.page().setWebChannel(self.channel)
        
        self.popups = []

    def createWindow(self, type):
        popup_view = CustomWebEngineView(self.backend_obj)
        popup_window = QMainWindow(self.window())
        popup_window.setWindowTitle("Print / Preview Invoice")
        popup_window.resize(1000, 750)
        popup_window.setCentralWidget(popup_view)
        popup_window.show()
        
        # Keep reference to prevent garbage collection
        self.popups.append(popup_window)
        popup_window.destroyed.connect(lambda: self.popups.remove(popup_window) if popup_window in self.popups else None)
        
        # Connect printRequested signal for the popup
        popup_view.page().printRequested.connect(lambda: handle_print_requested(popup_view.page()))
        
        return popup_view

# -------------------------------------------------------------
# Main Application Window
# -------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self, backend_obj):
        super().__init__()
        self.setWindowTitle("GST Invoice System")
        self.resize(1300, 850)
        self.backend_obj = backend_obj

        # Load and set default company favicon dynamically
        icon_path = self.get_window_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        # Initialize custom web view to support popups
        self.web_view = CustomWebEngineView(self.backend_obj)
        self.web_view.setUrl(QUrl("app://app/index.html"))
        
        # Connect printRequested signal for the main window
        self.web_view.page().printRequested.connect(lambda: handle_print_requested(self.web_view.page()))
        
        self.setCentralWidget(self.web_view)

    def get_window_icon_path(self):
        try:
            if os.path.exists(DB_PATH):
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT favicon_url FROM company_profile WHERE is_default=1 LIMIT 1")
                row = cursor.fetchone()
                conn.close()
                if row and row['favicon_url']:
                    # favicon_url format: "/uploads/favicons/uuid_favicon.png"
                    rel_path = row['favicon_url'].replace('/uploads/', '')
                    file_path = os.path.join(UPLOADS_DIR, rel_path.replace('/', os.sep))
                    if os.path.exists(file_path):
                        return file_path
        except Exception as e:
            print(f"[*] Icon load error: {e}", file=sys.stderr)
        return None

# -------------------------------------------------------------
# Execution Entry Point
# -------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("      GST INVOICE SYSTEM - STARTING UP (DESKTOP)      ")
    print("=" * 50)

    # Initialize Qt Application
    qt_app = QApplication(sys.argv)

    # Instantiate API backend bridge
    backend_obj = Backend(app)

    # Instantiate scheme handler
    handler = FastAPIUrlSchemeHandler(app)

    # Register the scheme handler on the default WebEngine profile
    profile = QWebEngineProfile.defaultProfile()
    profile.installUrlSchemeHandler(SCHEME_NAME, handler)
    
    # Register the file download handler
    profile.downloadRequested.connect(handle_download)

    # Start Main Window
    window = MainWindow(backend_obj)
    window.show()

    # Run Qt main loop
    sys.exit(qt_app.exec())
