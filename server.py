import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"NYP SEG Telegram Bot Server is Running!")

    # Suppress default HTTP logging to keep Render logs clean
    def log_message(self, format, *args):
        return

def start_dummy_server():
    # Render assigns a dynamic port via the PORT environment variable.
    # Default to 10000 only if running locally and PORT isn't set.
    port = int(os.environ.get("PORT", 10000))
    server_address = ("0.0.0.0", port)
    
    try:
        server = HTTPServer(server_address, HealthCheckHandler)
        print(f"Health check server listening on port {port}...")
        server.serve_forever()
    except Exception as e:
        print(f"Failed to start health check server: {e}")

def run_server():
    # Run the server on a separate daemon thread so it doesn't block the Telegram bot
    server_thread = threading.Thread(target=start_dummy_server, daemon=True)
    server_thread.start()