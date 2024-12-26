import os
import sys
import subprocess
import time
import logging
import signal
import webbrowser
import socket
import psutil
import matplotlib
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

matplotlib.use('Agg')

class AutomaticEmailApp:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.is_running: bool = True
        self.ports = {'frontend': 3000, 'backend': 8000}
        self.max_retries = 3
        
        # Set up paths based on execution context
        if getattr(sys, 'frozen', False):
            # Running as executable
            self.base_path = Path(sys._MEIPASS)
            self.app_path = Path(os.path.dirname(sys.executable))
        else:
            # Running as script
            self.base_path = Path(__file__).parent
            self.app_path = self.base_path

        # Set up derived paths
        self.backend_path = self.base_path / 'backend'
        self.frontend_path = self.base_path / 'src'
        self.next_build_path = self.app_path / '.next'
        
        self.setup_logging()
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def setup_logging(self) -> None:
        log_file = self.app_path / 'EmailApp.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        logging.info("Initialising Automatic Email Application...")

    def ensure_deps_installed(self) -> bool:
        try:
            if not (self.app_path / 'node_modules').exists():
                logging.info("Installing npm dependencies...")
                install_cmd = ['npm', 'install']
                kwargs = {
                    'cwd': str(self.app_path),
                    'env': os.environ.copy()
                }
                
                if os.name == 'nt':
                    kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                
                process = subprocess.run(install_cmd, **kwargs)
                if process.returncode != 0:
                    logging.error("Failed to install npm dependencies")
                    return False
            return True
        except Exception as e:
            logging.error(f"Failed to install dependencies: {str(e)}")
            return False

    def ensure_next_build(self) -> bool:
        try:
            if not self.next_build_path.exists():
                logging.info("Building Next.js application...")
                if not self.ensure_deps_installed():
                    return False
                    
                build_cmd = ['npm', 'run', 'build']
                kwargs = {
                    'cwd': str(self.app_path),
                    'env': os.environ.copy()
                }
                
                if os.name == 'nt':
                    kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                
                process = subprocess.run(build_cmd, **kwargs)
                if process.returncode != 0:
                    logging.error("Next.js build failed")
                    return False
            return True
        except Exception as e:
            logging.error(f"Failed to build Next.js: {str(e)}")
            return False

    def check_env_files(self) -> bool:
        try:
            # When running as exe, files are in _MEIPASS
            if getattr(sys, 'frozen', False):
                backend_env = Path(sys._MEIPASS) / 'backend' / '.env'
                frontend_env_local = Path(sys._MEIPASS) / 'src' / '.env.local'
            else:
                # When running as script, use relative paths
                backend_env = self.backend_path / '.env'
                frontend_env_local = self.frontend_path / '.env.local'
            
            # Log the paths we're checking
            logging.info(f"Checking backend .env at: {backend_env}")
            logging.info(f"Checking frontend .env.local at: {frontend_env_local}")
            
            if not backend_env.exists():
                logging.error(f"Backend .env file not found at {backend_env}")
                return False
                
            if not frontend_env_local.exists():
                logging.error(f"Frontend .env.local file not found at {frontend_env_local}")
                return False
                
            # Log environment file contents (excluding sensitive data)
            with open(backend_env) as f:
                env_contents = f.read()
                logging.info("Backend .env file found with keys: " + 
                            ", ".join(line.split('=')[0] for line in env_contents.splitlines() if '=' in line))
                
            with open(frontend_env_local) as f:
                env_contents = f.read()
                logging.info("Frontend .env.local file found with keys: " + 
                            ", ".join(line.split('=')[0] for line in env_contents.splitlines() if '=' in line))
            
            # Store paths for later use
            self.backend_env_path = backend_env
            self.frontend_env_path = frontend_env_local
            return True
        
        except Exception as e:
            logging.error(f"Error checking environment files: {str(e)}")
            return False

    def load_environment(self) -> bool:
        """Load and validate environment variables."""
        try:
            if not self.check_env_files():
                return False
            
            # Load environment files
            backend_env = self.backend_path / '.env'
            frontend_env_local = self.frontend_path / '.env.local'
            
            load_dotenv(dotenv_path=backend_env)
            load_dotenv(dotenv_path=frontend_env_local)
            
            # Validate required variables
            required_vars = [
                'API_KEY',
                'SMTP_SERVER',
                'SMTP_SENDER',
                'ADMIN_EMAIL',
                'NEXT_PUBLIC_API_URL',
                'NEXT_PUBLIC_API_KEY'
            ]
            
            missing = [var for var in required_vars if not os.getenv(var)]
            if missing:
                logging.error("Missing environment variables: " + ", ".join(missing))
                return False
            
            # Validate API URL format
            api_url = os.getenv('NEXT_PUBLIC_API_URL', '')
            if not api_url.startswith(('http://', 'https://')):
                logging.error(f"Invalid API URL format: {api_url}")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Environment loading failed: {str(e)}")
            return False

    def check_port(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) != 0

    def wait_for_port(self, port: int, timeout: int = 30) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.check_port(port):
                return True
            time.sleep(1)
        return False

    def start_backend(self) -> bool:
        try:
            if not self.check_port(self.ports['backend']):
                logging.error(f"Port {self.ports['backend']} is in use")
                return False

            # Use Python executable from the system instead of bundled one
            if getattr(sys, 'frozen', False):
                # Get the system's Python path from registry when frozen
                import winreg
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Python\PythonCore\3.9\InstallPath') as key:
                        python_dir = winreg.QueryValue(key, '')
                        python_path = os.path.join(python_dir, 'python.exe')
                except:
                    # Fallback to running in the current process
                    python_path = None
            else:
                python_path = sys.executable

            working_dir = str(self.base_path)
            
            if python_path:
                # Start backend as a separate process if we found Python
                cmd = [
                    python_path,
                    '-m', 'uvicorn',
                    'backend.api:app',
                    '--host', '0.0.0.0',
                    '--port', str(self.ports['backend']),
                    '--log-level', 'debug'
                ]
                
                logging.info(f"Starting backend with command: {' '.join(cmd)}")
                logging.info(f"Working directory: {working_dir}")
                
                process = subprocess.Popen(
                    cmd,
                    cwd=working_dir,
                    env={
                        **os.environ.copy(),
                        'PYTHONPATH': working_dir
                    },
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=1,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                self.processes['backend'] = process
                
                # Wait for server to start
                if not self.wait_for_port(self.ports['backend']):
                    logging.error("Backend server failed to start")
                    return False
                    
                return True
                
            else:
                # Run in current process if we couldn't find Python
                logging.info("Starting backend in current process")
                import uvicorn
                import threading
                
                def run_server():
                    uvicorn.run(
                        "backend.api:app",
                        host="0.0.0.0",
                        port=self.ports['backend'],
                        log_level="debug"
                    )
                
                server_thread = threading.Thread(target=run_server)
                server_thread.daemon = True
                server_thread.start()
                
                # Wait for server to start
                if not self.wait_for_port(self.ports['backend']):
                    logging.error("Backend server failed to start")
                    return False
                    
                return True
                    
        except Exception as e:
            logging.error(f"Backend startup failed: {str(e)}")
            return False
        
    
    def start_frontend(self) -> bool:
        try:
            if not self.check_port(self.ports['frontend']):
                logging.error(f"Port {self.ports['frontend']} is in use")
                return False
                
            if getattr(sys, 'frozen', False):
                # In frozen state, serve the static build
                from http.server import HTTPServer, SimpleHTTPRequestHandler
                import mimetypes
                
                # Add common MIME types
                mimetypes.add_type('text/css', '.css')
                mimetypes.add_type('text/javascript', '.js')
                mimetypes.add_type('image/x-icon', '.ico')
                mimetypes.add_type('application/json', '.json')
                
                # Try different directories in order of preference
                possible_dirs = [
                    self.base_path / 'src' / 'build',   # Next.js static export
                    self.base_path / 'build',           # Alternative static export location
                    self.base_path / 'src',             # Source directory
                    self.base_path / '.next',           # Next.js build directory
                ]
                
                working_dir = None
                for dir_path in possible_dirs:
                    if dir_path.exists():
                        working_dir = dir_path
                        break
                        
                if not working_dir:
                    logging.error("Could not find valid frontend directory")
                    return False
                    
                logging.info(f"Serving frontend from: {working_dir}")
                os.chdir(str(working_dir))
                
                class ExtendedHandler(SimpleHTTPRequestHandler):
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, directory=str(working_dir), **kwargs)
                    
                    def translate_path(self, path):
                        # Always serve index.html for root path
                        if path == '/':
                            return str(working_dir / 'index.html')
                        elif path == '/favicon.ico':
                            favicon_path = working_dir / 'favicon.ico'
                            if favicon_path.exists():
                                return str(favicon_path)
                            else:
                                return str(working_dir / 'static' / 'favicon.ico')
                        return super().translate_path(path)
                    
                    def send_error(self, code, message=None, explain=None):
                        if code == 404 and self.path == '/':
                            # Serve index.html for 404 on root path
                            try:
                                with open(str(working_dir / 'index.html'), 'rb') as f:
                                    content = f.read()
                                self.send_response(200)
                                self.send_header('Content-Type', 'text/html')
                                self.send_header('Content-Length', len(content))
                                self.end_headers()
                                self.wfile.write(content)
                                return
                            except:
                                pass
                        return super().send_error(code, message, explain)
                    
                    def log_message(self, format, *args):
                        if len(args) >= 3:
                            message = f"{args[0]} {args[1]} {args[2]}"
                        else:
                            message = format % args
                        logging.info(f"Frontend server: {message}")
                
                self.server = HTTPServer(('localhost', self.ports['frontend']), ExtendedHandler)
                logging.info(f"Starting frontend server on port {self.ports['frontend']}")
                
                # Start server in a separate thread
                import threading
                server_thread = threading.Thread(target=self.server.serve_forever)
                server_thread.daemon = True
                server_thread.start()
                
                return True
                
            else:
                # Development mode - use Next.js server
                if not self.ensure_next_build():
                    return False
                    
                cmd = ['npx', 'next', 'start', '-p', str(self.ports['frontend'])]
                
                logging.info(f"Starting frontend with command: {' '.join(cmd)}")
                logging.info(f"Working directory: {self.app_path}")
                
                kwargs = {
                    'cwd': str(self.app_path),
                    'env': os.environ.copy(),
                    'stdout': subprocess.PIPE,
                    'stderr': subprocess.PIPE,
                    'bufsize': 1,
                    'universal_newlines': True
                }
                
                if os.name == 'nt':
                    kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                
                # Start the frontend process
                self.processes['frontend'] = subprocess.Popen(cmd, **kwargs)
                
                # Wait for server to start
                if not self.wait_for_port(self.ports['frontend']):
                    logging.error("Frontend server failed to start")
                    return False
                    
                logging.info("Frontend server started successfully")
                return True
                
        except Exception as e:
            logging.error(f"Frontend startup failed: {str(e)}")
            return False
    
    def _read_process_output(self, process):
        while True:
            # Read stdout
            output = process.stdout.readline() if process.stdout else ''
            if output:
                logging.info(f"Backend output: {output.strip()}")

            # Read stderr
            error = process.stderr.readline() if process.stderr else ''
            if error:
                logging.error(f"Backend error: {error.strip()}")
            
            # Break if no more output
            if not output and not error:
                break

    def cleanup(self) -> None:
        # First cleanup all processes
        for name, process in self.processes.items():
            try:
                if process and process.poll() is None:
                    # Get process and children
                    parent = psutil.Process(process.pid)
                    children = parent.children(recursive=True)
                    
                    # Terminate children first
                    for child in children:
                        child.terminate()
                    parent.terminate()
                    
                    # Wait and force kill if necessary
                    gone, alive = psutil.wait_procs(children + [parent], timeout=3)
                    for p in alive:
                        p.kill()
                        
                    logging.info(f"Cleaned up {name} process")
            except Exception as e:
                logging.error(f"Error cleaning up {name} process: {str(e)}")
        
        # Cleanup frontend server if it exists
        try:
            if hasattr(self, 'server') and self.server:
                self.server.shutdown()
                self.server.server_close()
                logging.info("Cleaned up frontend server")
        except Exception as e:
            logging.error(f"Error cleaning up frontend server: {str(e)}")
            
        # Clear all stored references
        self.processes.clear()
        if hasattr(self, 'server'):
            self.server = None

    def signal_handler(self, signum: int, frame) -> None:
        print("\nReceived shutdown signal. Cleaning up...")
        self.is_running = False
        self.cleanup()
        sys.exit(0)

    def monitor_processes(self) -> None:
        retry_count = 0
        
        while self.is_running:
            for name, process in self.processes.items():
                if process.poll() is not None:
                    logging.error(f"{name} process stopped unexpectedly")
                    
                    if retry_count < self.max_retries:
                        logging.info(f"Attempting to restart {name}...")
                        if name == 'backend' and self.start_backend():
                            retry_count += 1
                            continue
                        elif name == 'frontend' and self.start_frontend():
                            retry_count += 1
                            continue
                    
                    self.is_running = False
                    break
            time.sleep(2)

    def run(self) -> None:
        try:
            logging.info("Starting Automatic Email Application...")
            
            if not self.load_environment():
                logging.error("Failed to load environment")
                return
            
            if not self.start_backend():
                logging.error("Failed to start backend")
                return
                
            if not self.start_frontend():
                logging.error("Failed to start frontend")
                self.cleanup()
                return
            
            url = f'http://localhost:{self.ports["frontend"]}'
            webbrowser.open(url)
            
            print(f"\nAutomatic Email Application is running!")
            print(f"Access the application at: {url}")
            print("Press Ctrl+C to stop the application")
            
            self.monitor_processes()
            
        except KeyboardInterrupt:
            print("\nShutting down gracefully...")
        except Exception as e:
            logging.error(f"Application error: {str(e)}")
        finally:
            self.cleanup()

if __name__ == "__main__":
    app = AutomaticEmailApp()
    app.run()