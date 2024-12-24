import os
import sys
import subprocess
import time
import logging
import signal
import webbrowser
import socket
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

class AutomaticEmailApp:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.is_running: bool = True
        self.ports = {'frontend': 3000, 'backend': 8000}
        
        # Set up paths
        if getattr(sys, 'frozen', False):
            self.base_path = Path(sys._MEIPASS)
            self.app_path = Path(os.path.dirname(sys.executable))
        else:
            self.base_path = Path(__file__).parent
            self.app_path = self.base_path
            
        self.backend_path = self.app_path / 'backend'
        self.frontend_path = self.app_path / 'src'
        self.next_build_path = self.app_path / '.next'
        
        # Set up logging first
        self.setup_logging()
        
        # Handle shutdown gracefully
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def setup_logging(self) -> None:
        log_file = self.app_path / 'run_app.log'
            
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

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
        backend_env = self.backend_path / '.env'
        frontend_env = self.frontend_path / '.env.local'
        
        if not backend_env.exists():
            logging.error(f"Backend .env file not found at {backend_env}")
            return False
            
        if not frontend_env.exists():
            logging.error(f"Frontend .env.local file not found at {frontend_env}")
            return False
            
        return True

    def load_environment(self) -> bool:
        try:
            if not self.check_env_files():
                return False
                
            backend_env = self.backend_path / '.env'
            frontend_env = self.frontend_path / '.env.local'
            
            load_dotenv(dotenv_path=backend_env)
            load_dotenv(dotenv_path=frontend_env)
            
            required_vars = [
                'API_KEY',
                'SMTP_SERVER',
                'NEXT_PUBLIC_API_URL',
                'NEXT_PUBLIC_API_KEY'
            ]
            
            missing = [var for var in required_vars if not os.getenv(var)]
            
            if missing:
                logging.error("Missing environment variables: " + ", ".join(missing))
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Environment loading failed: {str(e)}")
            return False

    def check_port(self, port: int) -> bool:
        """Simple port availability check"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) != 0
        
    def start_backend(self) -> bool:
        try:
            if not self.check_port(self.ports['backend']):
                logging.error(f"Port {self.ports['backend']} is in use")
                return False
            
            python_path = sys.executable if getattr(sys, 'frozen', False) else 'python'
            
            cmd = [
                python_path,
                '-m', 'uvicorn',
                'backend.api:app',
                '--host', '0.0.0.0',
                '--port', str(self.ports['backend'])
            ]
            
            # Use DEVNULL to prevent output buffer buildup
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
            
            self.processes['backend'] = subprocess.Popen(cmd, **kwargs)
            time.sleep(2)  # Brief pause for startup
            
            if self.processes['backend'].poll() is not None:
                _, stderr = self.processes['backend'].communicate()
                logging.error(f"Backend failed to start: {stderr}")
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
            
            cmd = ['npx', 'next', 'start', '-p', str(self.ports['frontend'])]
            
            # Use DEVNULL to prevent output buffer buildup
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
            
            self.processes['frontend'] = subprocess.Popen(cmd, **kwargs)
            time.sleep(2)  # Brief pause for startup
            
            if self.processes['frontend'].poll() is not None:
                _, stderr = self.processes['frontend'].communicate()
                logging.error(f"Frontend failed to start: {stderr}")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Frontend startup failed: {str(e)}")
            return False

    def signal_handler(self, signum: int, frame) -> None:
        """Clean shutdown on signal"""
        print("\nShutting down...")
        self.is_running = False
        self.cleanup()
        sys.exit(0)

    def cleanup(self) -> None:
        """Guaranteed cleanup of all processes"""
        for name, process in self.processes.items():
            try:
                if process and process.poll() is None:
                    process.terminate()
                    process.wait(timeout=2)
                    if process.poll() is None:
                        process.kill()
            except Exception as e:
                logging.error(f"Error cleaning up {name} process: {str(e)}")

    def log_process_output(self, process: subprocess.Popen, name: str) -> None:
        try:
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    logging.info(f"{name}: {line.strip()}")
        except Exception as e:
            logging.error(f"Error reading {name} output: {str(e)}")

    def monitor_processes(self) -> None:
        while self.is_running:
            for name, process in self.processes.items():
                if process.poll() is not None:
                    logging.error(f"{name} process stopped")
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