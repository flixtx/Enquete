import os
import json
import time
from http.server import BaseHTTPRequestHandler
import requests

UPSTASH_URL = os.environ.get('UPSTASH_REDIS_REST_URL', '').rstrip('/')
UPSTASH_TOKEN = os.environ.get('UPSTASH_REDIS_REST_TOKEN', '')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def redis_command(*args):
    url = f"{UPSTASH_URL}/pipeline"
    headers = {
        "Authorization": f"Bearer {UPSTASH_TOKEN}",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, json=[list(args)])
    data = resp.json()
    if isinstance(data, list) and data:
        result = data[0]
        if 'error' in result:
            raise Exception(result['error'])
        return result.get('result')
    return None

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/results':
            try:
                sim = int(redis_command('GET', 'feriado:sim') or 0)
                nao = int(redis_command('GET', 'feriado:nao') or 0)
                self.send_json(200, {'sim': sim, 'nao': nao})
            except Exception as e:
                self.send_json(500, {'error': str(e)})

        elif self.path in ('/', ''):
            self._serve_html()

        else:
            self.send_json(404, {'erro': f'Rota {self.path} não encontrada'})

    def do_POST(self):
        if self.path == '/api/vote':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(body)
                choice = data.get('choice')

                if choice not in ('sim', 'nao'):
                    raise ValueError('Escolha inválida')

                if not UPSTASH_URL or not UPSTASH_TOKEN:
                    raise Exception('Env vars não configuradas')

                key = f'feriado:{choice}'
                atual = int(redis_command('GET', key) or 0)
                redis_command('SET', key, str(atual + 1))

                self.send_json(200, {'success': True})
            except ValueError as e:
                self.send_json(400, {'error': str(e)})
            except Exception as e:
                import traceback
                print(traceback.format_exc())
                self.send_json(500, {'error': str(e)})
        else:
            self.send_json(404, {'erro': f'Rota {self.path} não encontrada'})

    def _serve_html(self):
        possible_paths = [
            os.path.join(BASE_DIR, 'index.html'),
            '/var/task/index.html',
            os.path.join(os.getcwd(), 'index.html'),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().encode('utf-8')
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)
                return
        self.send_json(404, {
            'erro': 'index.html não encontrado',
            'base_dir': BASE_DIR,
            'cwd': os.getcwd(),
            'listdir': os.listdir(BASE_DIR) if os.path.exists(BASE_DIR) else []
        })

    def send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
