import os
import json
import time
from http.server import BaseHTTPRequestHandler
import requests

UPSTASH_URL = os.environ.get('UPSTASH_REDIS_REST_URL', '').rstrip('/')
UPSTASH_TOKEN = os.environ.get('UPSTASH_REDIS_REST_TOKEN', '')

def redis_command(*args):
    path = '/'.join(arg.replace('/', '%2F') for arg in args)
    url = f"{UPSTASH_URL}/{path}"
    headers = {"Authorization": f"Bearer {UPSTASH_TOKEN}"}
    resp = requests.get(url)
    data = resp.json()
    if 'error' in data:
        raise Exception(data['error'])
    return data.get('result')

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Tratar requisições CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
def do_GET(self):
        print(f"GET request para: {self.path}")
        
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
        else:
            # Retornar HTML para requisições para a raiz ou outras rotas
            if self.path == '/' or self.path == '':
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                try:
                    with open('/var/task/public/enquete.html', 'r', encoding='utf-8') as f:
                        self.wfile.write(f.read().encode())
                except FileNotFoundError:
                    self.send_json(404, {'erro': 'Arquivo enquete.html não encontrado'})
            else:
                self.send_json(404, {'erro': f'Rota {self.path} não encontrada'})
    
def do_POST(self):
        print(f"POST request para: {self.path}")
        
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
    
def send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))