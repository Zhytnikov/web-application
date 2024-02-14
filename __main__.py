import json
import socket
import logging
import mimetypes
import urllib.parse
from pathlib import Path
from threading import Thread
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_DIR = Path()
BUFFER_SIZE = 1024
HTTP_PORT = 3000
HTTP_HOST = '0.0.0.0'
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000
MESSAGES = {}
STORAGE_PATH = Path('storage')
DELTA_TIME_ZONE = 0


class GoItFramework(BaseHTTPRequestHandler):

    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        if route.path == '/':
            self.send_html('index.html')
        elif route.path == '/message':
            self.send_html('message.html')
        else:
            file_path = BASE_DIR.joinpath(route.path[1:])
            if file_path.exists():
                self.send_static(file_path)
            else:
                self.send_html('error.html', 404)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length'))
        post_data = self.rfile.read(content_length)

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(post_data, (SOCKET_HOST, SOCKET_PORT))
        client_socket.close()

        self.send_response(302)
        self.send_header('Location', '/message')
        self.end_headers()

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

    def send_static(self, filename, status_code=200):
        self.send_response(status_code)
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header('Content-Type', mime_type)
        else:
            self.send_header('Content-Type', 'text/plain')

        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

def save_data_from_form(data):
    parse_data = urllib.parse.unquote_plus(data.decode())
    try:
        parse_dict = {key: value for key, value in [el.split('=') for el in parse_data.split('&')]}
        with open(STORAGE_PATH / 'data.json', 'w', encoding='utf-8') as file:
            timestamp = str(datetime.now() + timedelta(hours=DELTA_TIME_ZONE))
            MESSAGES[timestamp] = parse_dict
            json.dump(MESSAGES, file, ensure_ascii=False, indent=4)
            file.write('\n')
    except (ValueError, OSError) as error:
        logging.error(error)

def run_socket_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    logging.info("Starting socket server")
    try:
        while True:
            msg, address = server_socket.recvfrom(BUFFER_SIZE)
            logging.info(f"Socket received {address}: {msg}")
            save_data_from_form(msg)
    except KeyboardInterrupt:
        pass
    finally:
        server_socket.close()

def run_http_server(host, port):
    address = (host, port)
    http_server = HTTPServer(address, GoItFramework)
    logging.info("Starting http server")
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http_server.server_close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(threadName)s %(message)s")
    try:
        with open(STORAGE_PATH / 'data.json', 'r') as file:
            MESSAGES = json.load(file)
    except OSError as err:
        logging.error(err)
        STORAGE_PATH.mkdir(exist_ok=True, parents=True)

    http_server_thread = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    http_server_thread.start()

    socket_server_thread = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    socket_server_thread.start()
