import os
import json
import time
import sys
from http.server import BaseHTTPRequestHandler
import requests

# Adiciona o diretório atual ao path para garantir imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

UPSTASH_URL = os.environ.get('UPSTASH_REDIS_REST_URL', '').rstrip('/')
UPSTASH_TOKEN = os.environ.get('UPSTASH_REDIS_REST_TOKEN', '')

def redis_command(*args):
    """Executa qualquer comando Redis via REST API"""
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        raise Exception('Upstash Redis não configurado. Configure as variáveis de ambiente.')
    
    path = '/'.join(arg.replace('/', '%2F') for arg in args)
    url = f"{UPSTASH_URL}/{path}"
    headers = {"Authorization": f"Bearer {UPSTASH_TOKEN}"}
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
        if 'error' in data:
            raise Exception(data['error'])
        return data.get('result')
    except requests.exceptions.RequestException as e:
        raise Exception(f"Erro de conexão com Upstash: {str(e)}")

def handle_results():
    sim = int(redis_command('GET', 'feriado:sim') or 0)
    nao = int(redis_command('GET', 'feriado:nao') or 0)
    return {'sim': sim, 'nao': nao}

def handle_vote(body):
    data = json.loads(body)
    choice = data.get('choice')
    comment = data.get('comment', '').strip()
    
    if choice not in ('sim', 'nao'):
        raise ValueError('Escolha inválida')
    if not comment:
        raise ValueError('Observação obrigatória')
    if len(comment) > 600:
        raise ValueError('Máximo 600 caracteres')
    
    redis_command('INCR', f'feriado:{choice}')
    obs = {
        'escolha': choice,
        'texto': comment,
        'timestamp': int(time.time() * 1000)
    }
    redis_command('RPUSH', 'feriado:observacoes', json.dumps(obs))
    return {'success': True}

def handle_comments():
    items = redis_command('LRANGE', 'feriado:observacoes', '0', '-1')
    if not items:
        items = []
    comments = []
    for item in items:
        try:
            if isinstance(item, str):
                obj = json.loads(item)
            else:
                obj = item
            if obj.get('texto'):
                comments.append(obj)
        except:
            pass
    comments.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return {'comments': comments}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == '/api/results':
                result = handle_results()
                self.send_json(200, result)
            elif self.path == '/api/comments':
                result = handle_comments()
                self.send_json(200, result)
            else:
                self.send_json(404, {'error': 'Rota não encontrada'})
        except Exception as e:
            print(f"Erro no GET {self.path}: {str(e)}")
            self.send_json(500, {'error': str(e)})
    
    def do_POST(self):
        try:
            if self.path == '/api/vote':
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                result = handle_vote(body)
                self.send_json(200, result)
            else:
                self.send_json(404, {'error': 'Rota não encontrada'})
        except ValueError as e:
            self.send_json(400, {'error': str(e)})
        except Exception as e:
            print(f"Erro no POST {self.path}: {str(e)}")
            self.send_json(500, {'error': str(e)})
    
    def send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
