import os
import json
import time
from http.server import BaseHTTPRequestHandler
import requests

UPSTASH_URL = os.environ.get('UPSTASH_REDIS_REST_URL', '').rstrip('/')
UPSTASH_TOKEN = os.environ.get('UPSTASH_REDIS_REST_TOKEN', '')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def redis_command(*args):
    path = '/'.join(str(arg).replace('/', '%2F') for arg in args)
    url = f"{UPSTASH_URL}/{path}"
    headers = {"Authorization": f"Bearer {UPSTASH_TOKEN}"}
    resp = requests.get(url, headers=headers)
    data = resp.json()
    if 'error' in data:
        raise Exception(data['error'])
    return data.get('result')

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

        elif self.path == '/api/comments':
            try:
                items = redis_command('LRANGE', 'feriado:observacoes', '0', '-1') or []
                comments = []
                for item in items:
                    try:
                        obj = json.loads(item)
                        if obj.get('texto'):
                            comments.append(obj)
                    except:
                        pass
                comments.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                self.send_json(200, {'comments': comments})
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
                comment = data.get('comment', '').strip()

                if choice not in ('sim', 'nao'):
                    raise ValueError('Escolha inválida')
                if not comment:
                    raise ValueError('Observação obrigatória')
                if len(comment) > 600:
                    raise ValueError('Máximo 600 caracteres')

                if not UPSTASH_URL or not UPSTASH_TOKEN:
                    raise Exception(f'Env vars não configuradas: URL={bool(UPSTASH_URL)} TOKEN={bool(UPSTASH_TOKEN)}')

                redis_command('INCR', f'feriado:{choice}')
                obs = {
                    'escolha': choice,
                    'texto': comment,
                    'timestamp': int(time.time() * 1000)
                }
                redis_command('RPUSH', 'feriado:observacoes', json.dumps(obs))
                self.send_json(200, {'success': True})
            except ValueError as e:
                self.send_json(400, {'error': str(e)})
            except Exception as e:
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
