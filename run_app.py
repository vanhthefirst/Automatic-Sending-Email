import os
import sys
import subprocess
import time

class AutomaticEmailApp:
    def __init__(self):
        self.frontend_process = None
        self.backend_process = None
        
    def start_backend(self):
        try:
            self.backend_process = subprocess.Popen(
                ['python', '-m', 'uvicorn', 'backend.api:app', '--host', '0.0.0.0', '--port', '8000'],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            time.sleep(5)
            print("Backend server started successfully")
        except Exception as e:
            print(f"Error starting backend: {e}")
            sys.exit(1)

    def start_frontend(self):
        try:
            npm_path = 'C:\\Program Files\\nodejs\\npm.cmd'
            self.frontend_process = subprocess.Popen(
                [npm_path, 'run', 'dev'],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=os.getcwd()  # Use current working directory
            )
            print("Frontend server started successfully")
        except Exception as e:
            print(f"Error starting frontend: {e}")
            sys.exit(1)

    def cleanup(self):
        if self.frontend_process:
            self.frontend_process.terminate()
        if self.backend_process:
            self.backend_process.terminate()

    def run(self):
        try:
            self.start_backend()
            self.start_frontend()
            print("\nApplication is running!")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping application...")
        finally:
            self.cleanup()

if __name__ == "__main__":
    app = AutomaticEmailApp()
    app.run()