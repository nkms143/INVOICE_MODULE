import PyInstaller.__main__ as PyInstallerMain
import os
import shutil
import sys
import subprocess

# Get the root directory (one level up from execution)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def build():
    print("=" * 50)
    print("      BUILDING GST INVOICE SYSTEM BUNDLE      ")
    print("=" * 50)
    
    # Change working directory to ROOT_DIR to simplify paths and avoid quoting issues with spaces
    os.chdir(ROOT_DIR)
    print(f"[*] Working directory: {os.getcwd()}")
    
    # Clean previous builds
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            print(f"[*] Cleaning {folder}...")
            shutil.rmtree(folder)

    # PyInstaller arguments
    # Note: On Windows, the separator for --add-data is ';'
    # We use os.path.join to ensure correct backslashes on Windows for the source path
    args = [
        os.path.join('execution', 'main.py'),  # Entry point
        '--name=GST_Invoice_System',           # App name
        '--onedir',                           # Create a folder
        '--noconsole',                        # No command window
        '--noupx',                            # Disable UPX compression to avoid AV false positives
        
        # Add Data Folders (using os.path.join for native separators)
        f'--add-data=frontend{os.path.sep}*;frontend',
        f'--add-data=Templates{os.path.sep}*;Templates',
        f'--add-data=execution{os.path.sep}uploads{os.path.sep}*;execution{os.path.sep}uploads',
        f'--add-data=execution{os.path.sep}invoices.db;execution',
        
        # Hidden imports for Uvicorn
        '--hidden-import=uvicorn.logging',
        '--hidden-import=uvicorn.loops',
        '--hidden-import=uvicorn.loops.auto',
        '--hidden-import=uvicorn.protocols',
        '--hidden-import=uvicorn.protocols.http',
        '--hidden-import=uvicorn.protocols.http.auto',
        '--hidden-import=uvicorn.protocols.websockets',
        '--hidden-import=uvicorn.protocols.websockets.auto',
        '--hidden-import=uvicorn.lifespan',
        '--hidden-import=uvicorn.lifespan.on',
    ]

    print("[*] Running PyInstaller...")
    try:
        PyInstallerMain.run(args)
        print("\n" + "=" * 50)
        print("[SUCCESS] Build complete! Check the 'dist/GST_Invoice_System' folder.")
        print("=" * 50)
    except Exception as e:
        print(f"[-] PyInstaller failed: {e}")
        return

    # --- INNO SETUP INSTALLER STEP ---
    print("\n[*] Looking for Inno Setup Compiler (ISCC.exe)...")
    
    # Common locations for ISCC.exe
    iscc_paths = [
        "ISCC.exe", # If in PATH
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe"
    ]
    
    iscc_found = None
    for path in iscc_paths:
        try:
            # Check if it works
            subprocess.run([path, "/?"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            iscc_found = path
            break
        except FileNotFoundError:
            continue

    if iscc_found:
        print(f"[+] Found ISCC at: {iscc_found}")
        print("[*] Compiling installer...")
        iss_script = os.path.join("execution", "installer_config.iss")
        try:
            subprocess.run([iscc_found, iss_script], check=True)
            print("\n" + "=" * 50)
            print("[SUCCESS] Installer created in 'dist_setup' folder!")
            print("=" * 50)
        except subprocess.CalledProcessError as e:
            print(f"[-] Installer compilation failed: {e}")
    else:
        print("[-] Inno Setup Compiler (ISCC.exe) not found.")
        print("[TIP] Install Inno Setup or add it to your PATH to automate Setup.exe creation.")

if __name__ == "__main__":
    build()
