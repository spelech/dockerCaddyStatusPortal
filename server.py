import http.server
import socketserver
import json
import os
import subprocess

PORT = int(os.getenv("PORT", 8040))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == "/api/containers":
            self.send_containers_json()
        elif self.path == "/api/refresh":
            self.refresh_containers_data()
        else:
            super().do_GET()

    def send_containers_json(self):
        json_path = os.path.join(DIRECTORY, "data.json")
        if not os.path.exists(json_path):
            # Run parser first
            self.run_parser()
            
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        except Exception as e:
            self.send_error_response(500, str(e))

    def refresh_containers_data(self):
        try:
            self.run_parser()
            self.send_containers_json()
        except Exception as e:
            self.send_error_response(500, str(e))

    def run_parser(self):
        parser_path = os.path.join(DIRECTORY, "parser.py")
        subprocess.run(["python3", parser_path], check=True)

    def send_error_response(self, code, message):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode("utf-8"))

if __name__ == "__main__":
    # Ensure data.json exists at start
    parser_path = os.path.join(DIRECTORY, "parser.py")
    subprocess.run(["python3", parser_path], check=True)
    
    # Change working dir to directory of this file
    os.chdir(DIRECTORY)
    
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Caddy & Auth Portal serving at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
