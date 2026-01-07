#!/usr/bin/env python3
"""
🚀 Децентрализованная AI сеть MVP - Универсальная версия
Поддержка IPv4/IPv6, автоматическое определение адресов
CORS поддержка для фронтенда
"""

import socket
import threading
import json
import time
import random
import math
import hashlib
import logging
import argparse
import os
import sys
import uuid
from typing import Dict, List, Optional, Any

# Веб-интерфейс
try:
    from flask import Flask, jsonify, request
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️ Flask не установлен. Установите: pip install flask")
    sys.exit(1)

# CORS поддержка
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    print("⚠️ Flask-CORS не установлен. Установите: pip install flask-cors")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("AI-Network")

# ========== МАТЕМАТИЧЕСКИЕ УТИЛИТЫ ==========
class MathUtils:
    """Математические утилиты для вычислений"""
    
    @staticmethod
    def random_matrix(size: int) -> List[List[float]]:
        """Создать случайную матрицу заданного размера"""
        return [[random.random() for _ in range(size)] for _ in range(size)]
    
    @staticmethod
    def matrix_multiply(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        """Умножение матриц (наивная реализация)"""
        n = len(a)
        result = [[0.0 for _ in range(n)] for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                for k in range(n):
                    result[i][j] += a[i][k] * b[k][j]
        
        return result
    
    @staticmethod
    def sigmoid(x: float) -> float:
        """Сигмоидная функция активации"""
        return 1.0 / (1.0 + math.exp(-x))
    
    @staticmethod
    def vector_dot(v1: List[float], v2: List[float]) -> float:
        """Скалярное произведение векторов"""
        return sum(x * y for x, y in zip(v1, v2))

# ========== ПРОСТАЯ НЕЙРОННАЯ СЕТЬ ==========
class SimpleNeuralNetwork:
    """Простая нейронная сеть с одним скрытым слоем"""
    
    def __init__(self, input_size: int = 3, hidden_size: int = 4, output_size: int = 2):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        # Инициализация весов случайными значениями
        self.w1 = [[random.uniform(-0.5, 0.5) for _ in range(hidden_size)] 
                   for _ in range(input_size)]
        self.b1 = [0.0] * hidden_size
        
        self.w2 = [[random.uniform(-0.5, 0.5) for _ in range(output_size)] 
                   for _ in range(hidden_size)]
        self.b2 = [0.0] * output_size
    
    def predict(self, inputs: List[float]) -> List[float]:
        """Прямой проход (инференс)"""
        # Проверка входных данных
        if len(inputs) != self.input_size:
            raise ValueError(f"Ожидается {self.input_size} входов, получено {len(inputs)}")
        
        # Скрытый слой
        hidden = [0.0] * self.hidden_size
        for i in range(self.hidden_size):
            weighted_sum = sum(inputs[j] * self.w1[j][i] for j in range(self.input_size))
            hidden[i] = MathUtils.sigmoid(weighted_sum + self.b1[i])
        
        # Выходной слой
        outputs = [0.0] * self.output_size
        for i in range(self.output_size):
            weighted_sum = sum(hidden[j] * self.w2[j][i] for j in range(self.hidden_size))
            outputs[i] = MathUtils.sigmoid(weighted_sum + self.b2[i])
        
        return outputs

# ========== СЕТЕВЫЕ УТИЛИТЫ ==========
class NetworkUtils:
    """Утилиты для работы с сетью"""
    
    @staticmethod
    def get_all_ip_addresses() -> List[str]:
        """Получить все IP адреса сервера"""
        addresses = []
        try:
            hostname = socket.gethostname()
            
            # Получаем все адреса
            for info in socket.getaddrinfo(hostname, None):
                address = info[4][0]
                if address not in addresses:
                    addresses.append(address)
            
            # Если не нашли, пробуем альтернативные методы
            if not addresses:
                try:
                    # Внешний IP
                    import urllib.request
                    external_ip = urllib.request.urlopen('https://api.ipify.org', timeout=3).read().decode()
                    addresses.append(external_ip)
                except:
                    pass
                
                # Локальные адреса
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                    s.close()
                    if local_ip not in addresses:
                        addresses.append(local_ip)
                except:
                    pass
        except Exception as e:
            logger.warning(f"Ошибка получения IP адресов: {e}")
            addresses = ["127.0.0.1", "0.0.0.0", "::1"]
        
        return addresses
    
    @staticmethod
    def get_best_public_ip() -> str:
        """Получить лучший публичный IP для подключения"""
        try:
            addresses = NetworkUtils.get_all_ip_addresses()
            
            # Предпочитаем IPv4 адреса
            ipv4_addresses = [ip for ip in addresses if ':' not in ip and not ip.startswith('127.')]
            if ipv4_addresses:
                # Ищем публичный IPv4
                public_ipv4 = [ip for ip in ipv4_addresses if not (
                    ip.startswith('10.') or 
                    ip.startswith('172.16.') or 
                    ip.startswith('192.168.')
                )]
                if public_ipv4:
                    return public_ipv4[0]
                return ipv4_addresses[0]  # Возвращаем любой IPv4
            
            # Если нет IPv4, ищем IPv6
            ipv6_addresses = [ip for ip in addresses if ':' in ip and ip != '::1']
            if ipv6_addresses:
                return ipv6_addresses[0]
            
            # По умолчанию
            return "0.0.0.0"
            
        except Exception as e:
            logger.error(f"Ошибка определения публичного IP: {e}")
            return "0.0.0.0"
    
    @staticmethod
    def create_socket() -> socket.socket:
        """Создать сокет с правильными настройками"""
        try:
            # Сначала пытаемся создать сокет, поддерживающий IPv6
            if socket.has_ipv6:
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # Включаем поддержку IPv4 через IPv6
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                return sock
        except:
            pass
        
        # Если IPv6 не поддерживается или произошла ошибка, используем IPv4
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock
    
    @staticmethod
    def create_client_socket() -> socket.socket:
        """Создать сокет для клиента с улучшенными настройками"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return sock

# ========== КООРДИНАТОР СЕТИ ==========
class NetworkCoordinator:
    """Координатор децентрализованной сети"""
    
    def __init__(self, host: str = None, worker_port: int = 8888, web_port: int = 8890):
        # Ключевое исправление: всегда используем публичный IP для web сервера
        if host is None or host == "" or host == "0.0.0.0":
            # Получаем публичный IP
            self.public_host = NetworkUtils.get_best_public_ip()
            if self.public_host == "0.0.0.0":
                # Если не смогли определить, используем статический IP
                self.public_host = "185.185.142.113"
            self.host = "0.0.0.0"  # Flask будет слушать на всех интерфейсах
        else:
            self.host = host
            self.public_host = host
        
        self.worker_port = worker_port
        self.web_port = web_port
        
        # Данные сети
        self.workers: Dict[str, Dict] = {}
        self.tasks: Dict[str, Dict] = {}
        self.task_queue: List[str] = []
        
        # Синхронизация
        self.lock = threading.RLock()
        self.running = False
        
        # Веб-сервер с CORS
        self.app = Flask(__name__)
        
        # Настройка CORS - РУЧНАЯ НАСТРОЙКА для надежности
        @self.app.after_request
        def add_cors_headers(response):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response
        
        # Дополнительно настраиваем flask-cors если доступен
        if CORS_AVAILABLE:
            CORS(self.app, resources={r"/api/*": {"origins": "*"}})
            logger.info("CORS включен через flask-cors")
        else:
            logger.info("CORS включен через ручные заголовки")
        
        self._setup_web_routes()
        
        logger.info(f"Инициализация координатора на {self.host}:{self.worker_port}")
        logger.info(f"Публичный адрес: {self.public_host}")
    
    def _setup_web_routes(self):
        """Настройка маршрутов веб-сервера с CORS"""
        
        @self.app.route('/')
        def index():
            return self._get_web_interface()
        
        @self.app.route('/api/status', methods=['GET', 'OPTIONS'])
        def api_status():
            if request.method == 'OPTIONS':
                return '', 200
            return jsonify({
                'status': 'running',
                'coordinator': {
                    'host': self.public_host,
                    'worker_port': self.worker_port,
                    'web_port': self.web_port,
                    'uptime': getattr(self, 'start_time', time.time())
                },
                'cors': 'enabled',
                'api_version': '1.0'
            })
        
        @self.app.route('/api/stats', methods=['GET', 'OPTIONS'])
        def api_stats():
            if request.method == 'OPTIONS':
                return '', 200
            with self.lock:
                stats = self._get_stats()
            return jsonify(stats)
        
        @self.app.route('/api/tasks', methods=['GET', 'OPTIONS'])
        def api_tasks():
            if request.method == 'OPTIONS':
                return '', 200
            with self.lock:
                # Преобразуем задачи в список для JSON сериализации
                tasks_list = []
                for task_id, task in self.tasks.items():
                    task_copy = task.copy()
                    # Преобразуем любые несериализуемые объекты
                    if 'result' in task_copy and task_copy['result']:
                        if hasattr(task_copy['result'], '__dict__'):
                            task_copy['result'] = str(task_copy['result'])
                    tasks_list.append(task_copy)
                
                return jsonify({
                    'tasks': tasks_list,
                    'queue': self.task_queue,
                    'total_tasks': len(tasks_list)
                })
        
        @self.app.route('/api/submit', methods=['POST', 'OPTIONS'])
        def api_submit():
            if request.method == 'OPTIONS':
                return '', 200
            
            # Добавляем заголовки CORS
            response_headers = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, Accept'
            }
            
            try:
                # Проверяем Content-Type
                if not request.is_json:
                    return jsonify({
                        'status': 'error',
                        'message': 'Content-Type должен быть application/json'
                    }), 400, response_headers
                
                data = request.get_json() or {}
                task_type = data.get('type', 'matrix_mult')
                task_data = data.get('data', {})
                
                task_id = self._create_task(task_type, task_data)
                
                return jsonify({
                    'status': 'success',
                    'task_id': task_id,
                    'message': 'Задача создана',
                    'type': task_type
                }), 200, response_headers
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': str(e),
                    'error_type': type(e).__name__
                }), 400, response_headers
        
        @self.app.route('/api/workers', methods=['GET', 'OPTIONS'])
        def api_workers():
            if request.method == 'OPTIONS':
                return '', 200
            with self.lock:
                workers = []
                for worker_id, worker in self.workers.items():
                    workers.append({
                        'id': worker_id[:8],
                        'name': worker.get('name', 'unknown'),
                        'address': f"{worker['addr'][0]}:{worker['addr'][1]}",
                        'status': worker.get('status', 'unknown'),
                        'last_seen': worker.get('last_seen', time.time()),
                        'current_task': worker.get('current_task'),
                        'capabilities': worker.get('capabilities', {})
                    })
                
                return jsonify({
                    'workers': workers,
                    'total_workers': len(workers),
                    'connected_workers': len([w for w in workers if w['status'] == 'connected'])
                })
        
        @self.app.route('/api/health', methods=['GET', 'OPTIONS'])
        def api_health():
            """Проверка здоровья API"""
            if request.method == 'OPTIONS':
                return '', 200
            
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time(),
                'service': 'ai-network-coordinator',
                'version': '1.0.0',
                'host': self.public_host,
                'port': self.web_port
            })
        
        @self.app.route('/api/test', methods=['GET', 'OPTIONS'])
        def api_test():
            """Тестовый endpoint для проверки CORS"""
            if request.method == 'OPTIONS':
                return '', 200
            return jsonify({
                'message': 'CORS работает!',
                'method': request.method,
                'origin': request.headers.get('Origin', 'none'),
                'timestamp': time.time()
            })
    
    def _get_web_interface(self):
        """Генерация веб-интерфейса координатора"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>🤖 AI Network - Координатор</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #0f3460; color: white; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
                .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }}
                .card {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; backdrop-filter: blur(10px); }}
                .stat {{ font-size: 2em; font-weight: bold; color: #4cc9f0; }}
                .btn {{ background: #4cc9f0; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }}
                .api-info {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin-top: 30px; }}
                code {{ background: rgba(0,0,0,0.3); padding: 2px 5px; border-radius: 3px; }}
                .status-connected {{ color: #2ecc71; }}
                .status-disconnected {{ color: #e74c3c; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 AI Network Coordinator</h1>
                    <p>Децентрализованная сеть распределенных вычислений</p>
                    <p>Публичный адрес: <code>{self.public_host}:{self.web_port}</code></p>
                </div>
                
                <div class="cards">
                    <div class="card">
                        <h3>🌐 Сеть</h3>
                        <p>Web интерфейс: <code>{self.public_host}:{self.web_port}</code></p>
                        <p>Порт рабочих: <code>{self.worker_port}</code></p>
                        <p>Текущий хост: <code>{self.host}</code></p>
                    </div>
                    
                    <div class="card">
                        <h3>📊 Статистика</h3>
                        <div class="stat" id="workersCount">0</div>
                        <p>Активных рабочих</p>
                        <div class="stat" id="tasksCount">0</div>
                        <p>Всего задач</p>
                    </div>
                    
                    <div class="card">
                        <h3>🔧 Управление</h3>
                        <button class="btn" onclick="loadStats()">Обновить</button>
                        <button class="btn" onclick="testAPI()">Тест API</button>
                        <button class="btn" onclick="createTestTask()">Тест задача</button>
                        <button class="btn" onclick="window.open('/api/health', '_blank')">Проверка здоровья</button>
                    </div>
                </div>
                
                <div class="api-info">
                    <h3>📡 API Endpoints</h3>
                    <p><code>GET /api/status</code> - Статус координатора</p>
                    <p><code>GET /api/stats</code> - Статистика сети</p>
                    <p><code>GET /api/tasks</code> - Список задач</p>
                    <p><code>GET /api/workers</code> - Список рабочих</p>
                    <p><code>POST /api/submit</code> - Отправить задачу</p>
                    <p><code>GET /api/health</code> - Проверка здоровья</p>
                    <p><code>GET /api/test</code> - Тест CORS</p>
                    
                    <h3 style="margin-top: 20px;">🔗 Для фронтенда</h3>
                    <p>Используйте этот URL для подключения фронтенда:</p>
                    <p><code>http://{self.public_host}:{self.web_port}/api/</code></p>
                    <p>Пример JavaScript:</p>
                    <pre><code>
fetch('http://{self.public_host}:{self.web_port}/api/health')
  .then(response => response.json())
  .then(data => console.log(data));
                    </code></pre>
                </div>
            </div>
            
            <script>
                async function loadStats() {{
                    try {{
                        const response = await fetch('/api/stats');
                        const data = await response.json();
                        document.getElementById('workersCount').textContent = data.workers_count || 0;
                        document.getElementById('tasksCount').textContent = data.tasks_total || 0;
                        alert('Статистика обновлена!');
                    }} catch (error) {{
                        alert('Ошибка: ' + error.message);
                    }}
                }}
                
                async function testAPI() {{
                    try {{
                        const response = await fetch('/api/test');
                        const data = await response.json();
                        alert('API работает: ' + data.message);
                    }} catch (error) {{
                        alert('Ошибка API: ' + error.message);
                    }}
                }}
                
                async function createTestTask() {{
                    try {{
                        const response = await fetch('/api/submit', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{
                                type: 'matrix_mult',
                                data: {{ size: 5 }}
                            }})
                        }});
                        const data = await response.json();
                        alert('Задача создана: ' + data.task_id);
                    }} catch (error) {{
                        alert('Ошибка: ' + error.message);
                    }}
                }}
                
                // Загружаем статистику при старте
                loadStats();
                setInterval(loadStats, 5000);
            </script>
        </body>
        </html>
        """
        return html
    
    def _get_stats(self) -> Dict[str, Any]:
        """Получить статистику сети"""
        with self.lock:
            tasks_pending = len([t for t in self.tasks.values() if t.get('status') == 'pending'])
            tasks_running = len([t for t in self.tasks.values() if t.get('status') == 'running'])
            tasks_completed = len([t for t in self.tasks.values() if t.get('status') == 'completed'])
            tasks_failed = len([t for t in self.tasks.values() if t.get('status') == 'failed'])
            
            connected_workers = len([w for w in self.workers.values() if w.get('status') == 'connected'])
            
            return {
                'workers_count': connected_workers,
                'total_workers': len(self.workers),
                'tasks_total': len(self.tasks),
                'tasks_pending': tasks_pending,
                'tasks_running': tasks_running,
                'tasks_completed': tasks_completed,
                'tasks_failed': tasks_failed,
                'queue_length': len(self.task_queue),
                'timestamp': time.time(),
                'coordinator_uptime': time.time() - getattr(self, 'start_time', time.time()),
                'public_host': self.public_host,
                'web_port': self.web_port
            }
    
    def _create_task(self, task_type: str, task_data: Dict) -> str:
        """Создать новую задачу"""
        task_id = str(uuid.uuid4())[:12]
        
        with self.lock:
            self.tasks[task_id] = {
                'id': task_id,
                'type': task_type,
                'data': task_data,
                'status': 'pending',
                'created': time.time(),
                'worker': None,
                'result': None,
                'updated': time.time()
            }
            self.task_queue.append(task_id)
        
        logger.info(f"Создана задача {task_id} типа {task_type}")
        
        # Попробуем сразу назначить задачу
        self._assign_tasks()
        
        return task_id
    
    def _assign_tasks(self):
        """Назначить задачи свободным рабочим"""
        with self.lock:
            if not self.task_queue:
                return
            
            # Ищем свободных рабочих
            free_workers = []
            for worker_id, worker in self.workers.items():
                if worker.get('status') == 'connected' and not worker.get('current_task'):
                    free_workers.append(worker_id)
            
            if not free_workers:
                return
            
            # Назначаем задачи
            for worker_id in free_workers:
                if not self.task_queue:
                    break
                
                task_id = self.task_queue.pop(0)
                task = self.tasks.get(task_id)
                
                if task and task.get('status') == 'pending':
                    if self._send_task_to_worker(worker_id, task_id, task):
                        task['status'] = 'running'
                        task['worker'] = worker_id
                        task['started'] = time.time()
                        
                        self.workers[worker_id]['current_task'] = task_id
                        
                        logger.info(f"Задача {task_id} назначена рабочему {worker_id}")
    
    def _send_task_to_worker(self, worker_id: str, task_id: str, task: Dict) -> bool:
        """Отправить задачу рабочему"""
        try:
            with self.lock:
                worker = self.workers.get(worker_id)
                if not worker:
                    return False
                
                conn = worker.get('conn')
                if not conn:
                    return False
            
            task_message = {
                'type': 'task',
                'task_id': task_id,
                'task_type': task['type'],
                'data': task['data'],
                'timestamp': time.time()
            }
            
            message = json.dumps(task_message).encode()
            conn.sendall(message)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки задачи {task_id} рабочему {worker_id}: {e}")
            return False
    
    def _handle_worker_connection(self, conn: socket.socket, addr: tuple):
        """Обработка подключения рабочего"""
        worker_id = f"{addr[0]}:{addr[1]}-{int(time.time())}"
        
        logger.info(f"Новое подключение рабочего: {worker_id}")
        
        # Регистрируем рабочего
        with self.lock:
            self.workers[worker_id] = {
                'conn': conn,
                'addr': addr,
                'name': f"Worker_{worker_id[-6:]}",
                'status': 'connected',
                'last_seen': time.time(),
                'current_task': None,
                'capabilities': {},
                'connected_at': time.time()
            }
        
        try:
            # Устанавливаем таймаут
            conn.settimeout(30)
            
            # Отправляем приветственное сообщение
            welcome_msg = {
                'type': 'welcome',
                'worker_id': worker_id,
                'message': 'Добро пожаловать в AI Network!',
                'timestamp': time.time(),
                'coordinator': self.public_host,
                'web_port': self.web_port
            }
            welcome_json = json.dumps(welcome_msg)
            conn.sendall(welcome_json.encode())
            logger.info(f"Отправлено приветствие рабочему {worker_id}")
            
            # Ждем регистрацию от рабочего
            conn.settimeout(10)
            registered = False
            
            try:
                buffer = ""
                start_time = time.time()
                
                while not registered and time.time() - start_time < 10:
                    try:
                        conn.settimeout(0.5)
                        data = conn.recv(4096)
                        if data:
                            buffer += data.decode('utf-8', errors='ignore')
                            
                            # Пробуем найти JSON сообщение о возможностях
                            messages = self._extract_json_messages(buffer)
                            
                            for message in messages:
                                if message.get('type') == 'capabilities':
                                    # Сохраняем возможности рабочего
                                    with self.lock:
                                        if worker_id in self.workers:
                                            self.workers[worker_id]['capabilities'] = message.get('capabilities', {})
                                            self.workers[worker_id]['name'] = message.get('name', self.workers[worker_id]['name'])
                                            logger.info(f"Рабочий {worker_id} зарегистрирован как '{self.workers[worker_id]['name']}'")
                                            registered = True
                                            break
                                    
                            if registered:
                                break
                                
                    except socket.timeout:
                        continue
                    except Exception as e:
                        logger.error(f"Ошибка чтения регистрации: {e}")
                        break
                
                if not registered:
                    logger.warning(f"Не получена регистрация от рабочего {worker_id}")
                    
            except Exception as e:
                logger.error(f"Ошибка ожидания регистрации: {e}")
            
            # Возвращаем обычный таймаут для основного цикла
            conn.settimeout(30)
            
            # Основной цикл обработки
            buffer = ""
            while self.running:
                try:
                    # Получаем данные от рабочего
                    data = conn.recv(4096)
                    
                    if not data:
                        logger.info(f"Рабочий {worker_id} отключился")
                        break
                    
                    buffer += data.decode('utf-8', errors='ignore')
                    
                    # Обрабатываем все полные сообщения в буфере
                    messages = self._extract_json_messages(buffer)
                    
                    for message in messages:
                        self._process_worker_message(worker_id, conn, message)
                    
                    # Очищаем буфер от обработанных сообщений
                    buffer = self._clean_buffer(buffer)
                    
                    # Обновляем время последней активности
                    with self.lock:
                        if worker_id in self.workers:
                            self.workers[worker_id]['last_seen'] = time.time()
                    
                except socket.timeout:
                    continue
                except ConnectionResetError:
                    logger.info(f"Соединение с {worker_id} разорвано")
                    break
                except Exception as e:
                    logger.error(f"Ошибка обработки рабочего {worker_id}: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Ошибка соединения с {worker_id}: {e}")
        finally:
            # Удаляем рабочего только если соединение закрыто
            self._remove_worker(worker_id)
            try:
                conn.close()
            except:
                pass
    
    def _extract_json_messages(self, buffer: str) -> List[Dict]:
        """Извлечь все полные JSON сообщения из буфера"""
        messages = []
        start = 0
        depth = 0
        in_string = False
        escape = False
        
        for i, char in enumerate(buffer):
            if not in_string:
                if char == '{':
                    if depth == 0:
                        start = i
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        # Нашли полный JSON объект
                        try:
                            message = json.loads(buffer[start:i+1])
                            messages.append(message)
                        except json.JSONDecodeError:
                            # Пропускаем некорректный JSON
                            pass
                elif char == '"':
                    in_string = True
            else:
                if escape:
                    escape = False
                elif char == '\\':
                    escape = True
                elif char == '"':
                    in_string = False
        
        return messages
    
    def _clean_buffer(self, buffer: str) -> str:
        """Очистить буфер от обработанных JSON сообщений"""
        # Находим последнюю закрывающую скобку
        last_close = buffer.rfind('}')
        if last_close != -1:
            # Оставляем только данные после последнего полного JSON
            return buffer[last_close + 1:]
        return buffer
    
    def _process_worker_message(self, worker_id: str, conn: socket.socket, message: Dict):
        """Обработать сообщение от рабочего"""
        try:
            if message.get('type') == 'heartbeat':
                # Обновляем время последней активности
                with self.lock:
                    if worker_id in self.workers:
                        self.workers[worker_id]['last_seen'] = time.time()
                
                # Отправляем подтверждение
                ack = {'type': 'heartbeat_ack', 'timestamp': time.time()}
                conn.sendall(json.dumps(ack).encode())
                
            elif message.get('type') == 'capabilities':
                # Обновляем возможности (может прийти позже)
                with self.lock:
                    if worker_id in self.workers:
                        self.workers[worker_id]['capabilities'] = message.get('capabilities', {})
                        self.workers[worker_id]['name'] = message.get('name', self.workers[worker_id]['name'])
                        logger.info(f"Обновлены данные рабочего {worker_id}: {self.workers[worker_id]['name']}")
                
            elif message.get('type') == 'result':
                # Обработка результата задачи
                task_id = message.get('task_id')
                result = message.get('result', {})
                
                with self.lock:
                    if worker_id in self.workers:
                        self.workers[worker_id]['current_task'] = None
                    
                    if task_id in self.tasks:
                        if result.get('status') == 'success':
                            self.tasks[task_id]['status'] = 'completed'
                            self.tasks[task_id]['result'] = result
                            self.tasks[task_id]['completed'] = time.time()
                            logger.info(f"Задача {task_id} успешно выполнена")
                        else:
                            self.tasks[task_id]['status'] = 'failed'
                            self.tasks[task_id]['result'] = result
                            self.tasks[task_id]['failed'] = time.time()
                            logger.warning(f"Задача {task_id} завершилась с ошибкой")
                
                # Пробуем назначить следующую задачу
                self._assign_tasks()
                
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения от рабочего {worker_id}: {e}")
    
    def _remove_worker(self, worker_id: str):
        """Удалить отключившегося рабочего"""
        with self.lock:
            if worker_id in self.workers:
                # Возвращаем задачу в очередь если есть
                current_task = self.workers[worker_id].get('current_task')
                if current_task and current_task in self.tasks:
                    task = self.tasks[current_task]
                    if task['status'] == 'running':
                        task['status'] = 'pending'
                        task['worker'] = None
                        self.task_queue.insert(0, current_task)
                        logger.warning(f"Задача {current_task} возвращена в очередь")
                
                del self.workers[worker_id]
                logger.info(f"Рабочий {worker_id} удален")
    
    def _cleanup_inactive_workers(self):
        """Очистка неактивных рабочих"""
        while self.running:
            try:
                time.sleep(60)  # Проверяем каждую минуту
                
                current_time = time.time()
                to_remove = []
                
                with self.lock:
                    for worker_id, worker in self.workers.items():
                        last_seen = worker.get('last_seen', 0)
                        if current_time - last_seen > 120:  # 2 минуты без активности
                            to_remove.append(worker_id)
                
                for worker_id in to_remove:
                    logger.warning(f"Рабочий {worker_id} удален по таймауту")
                    try:
                        if worker_id in self.workers:
                            conn = self.workers[worker_id].get('conn')
                            if conn:
                                conn.close()
                    except:
                        pass
                    self._remove_worker(worker_id)
                    
            except Exception as e:
                logger.error(f"Ошибка очистки рабочих: {e}")
    
    def _run_worker_server(self):
        """Запуск сервера для рабочих"""
        try:
            server = NetworkUtils.create_socket()
            
            # Для привязки используем 0.0.0.0 для IPv4 или :: для IPv6
            bind_host = "0.0.0.0"  # Всегда слушаем на всех интерфейсах
            
            try:
                # Пытаемся привязаться ко всем интерфейсам (IPv6)
                server.bind(("::", self.worker_port))
                logger.info(f"Сервер привязан к [::]:{self.worker_port} (IPv6)")
            except:
                # Если не получилось, используем IPv4
                server.bind((bind_host, self.worker_port))
                logger.info(f"Сервер привязан к {bind_host}:{self.worker_port} (IPv4)")
            
            server.listen(10)
            server.settimeout(1)  # Таймаут для accept
            
            logger.info(f"Сервер для рабочих запущен. Подключение: {self.public_host}:{self.worker_port}")
            
            while self.running:
                try:
                    conn, addr = server.accept()
                    conn.settimeout(30)
                    
                    # Запускаем обработчик в отдельном потоке
                    thread = threading.Thread(
                        target=self._handle_worker_connection,
                        args=(conn, addr),
                        daemon=True
                    )
                    thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Ошибка принятия соединения: {e}")
        
        except Exception as e:
            logger.error(f"Ошибка запуска сервера: {e}")
            import traceback
            traceback.print_exc()
            self.running = False
    
    def start(self):
        """Запуск координатора"""
        self.running = True
        self.start_time = time.time()
        
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК AI NETWORK COORDINATOR")
        logger.info("=" * 60)
        logger.info(f"🌐 Веб-интерфейс: http://{self.public_host}:{self.web_port}")
        logger.info(f"📡 Порт для рабочих: {self.worker_port}")
        logger.info(f"🔗 Адрес для рабочих: {self.public_host}:{self.worker_port}")
        logger.info(f"🏠 Слушаем на: {self.host}:{self.web_port}")
        logger.info(f"✅ CORS: {'Enabled' if CORS_AVAILABLE else 'Manual headers'}")
        logger.info("=" * 60)
        
        # Запускаем сервер для рабочих
        worker_server_thread = threading.Thread(target=self._run_worker_server, daemon=True)
        worker_server_thread.start()
        
        # Запускаем очистку неактивных рабочих
        cleanup_thread = threading.Thread(target=self._cleanup_inactive_workers, daemon=True)
        cleanup_thread.start()
        
        # Запускаем обработчик задач
        task_processor_thread = threading.Thread(target=self._task_processor_loop, daemon=True)
        task_processor_thread.start()
        
        try:
            # Даем время серверу запуститься
            time.sleep(1)
            
            # Запускаем веб-сервер Flask
            import warnings
            warnings.filterwarnings("ignore", message=".*Werkzeug.*")
            
            logger.info("✅ Система запущена и готова к работе!")
            logger.info("👷 Ожидание подключения рабочих узлов...")
            
            # Важное исправление: Flask всегда слушает на всех интерфейсах
            self.app.run(
                host=self.host,  # 0.0.0.0 - слушаем на всех интерфейсах
                port=self.web_port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
            
        except KeyboardInterrupt:
            logger.info("Получен сигнал завершения...")
        except Exception as e:
            logger.error(f"Ошибка запуска Flask: {e}")
        finally:
            self.running = False
            logger.info("Координатор остановлен")
    
    def _task_processor_loop(self):
        """Цикл обработки задач"""
        while self.running:
            try:
                self._assign_tasks()
                time.sleep(2)
            except Exception as e:
                logger.error(f"Ошибка обработчика задач: {e}")
                time.sleep(5)

# ========== РАБОЧИЙ УЗЕЛ ==========
class WorkerNode:
    """Рабочий узел для выполнения задач"""
    
    def __init__(self, server_host: str, server_port: int = 8888, name: str = None):
        self.server_host = server_host
        self.server_port = server_port
        self.name = name or f"Worker_{os.getpid()}_{random.randint(1000, 9999)}"
        self.running = False
        self.connected = False
        self.worker_id = None
        self.connection_attempts = 0
        self.max_connection_attempts = 10
        self.reconnect_delay = 5
    
    def safe_connect(self) -> Optional[socket.socket]:
        """Безопасное подключение"""
        try:
            sock = NetworkUtils.create_client_socket()
            sock.settimeout(15)
            
            logger.info(f"Подключение к {self.server_host}:{self.server_port}...")
            sock.connect((self.server_host, self.server_port))
            
            sock.settimeout(30)
            logger.info(f"✅ Успешно подключено к {self.server_host}:{self.server_port}")
            return sock
            
        except socket.timeout:
            logger.error("⚠️ Таймаут подключения")
            return None
        except ConnectionRefusedError:
            logger.error("❌ Сервер отказал в подключении")
            return None
        except socket.gaierror as e:
            logger.error(f"❌ Ошибка разрешения адреса: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {type(e).__name__}: {e}")
            return None
    
    def register_with_server(self, sock: socket.socket) -> bool:
        """Регистрация на сервере"""
        try:
            # Ждем приветственное сообщение от сервера
            sock.settimeout(10)
            logger.info("⏳ Ожидание приветствия от сервера...")
            data = sock.recv(4096)
            
            if not data:
                logger.error("❌ Сервер не отправил данные")
                return False
            
            raw_response = data.decode('utf-8', errors='ignore')
            
            # Пробуем распарсить JSON
            try:
                response = json.loads(raw_response.strip())
            except json.JSONDecodeError:
                # Пробуем найти JSON в строке
                start_idx = raw_response.find('{')
                end_idx = raw_response.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_str = raw_response[start_idx:end_idx+1]
                    response = json.loads(json_str)
                else:
                    logger.error(f"❌ Не удалось распарсить JSON от сервера")
                    return False
            
            if response.get('type') == 'welcome':
                self.worker_id = response.get('worker_id')
                logger.info(f"✅ {response.get('message')}")
                logger.info(f"🆔 Ваш ID: {self.worker_id}")
                
                # Ждем немного перед отправкой регистрации
                time.sleep(0.1)
                
                # Отправляем регистрацию
                registration = {
                    'type': 'capabilities',
                    'name': self.name,
                    'timestamp': time.time(),
                    'capabilities': {
                        'cpu_cores': os.cpu_count() or 1,
                        'platform': sys.platform,
                        'python_version': sys.version.split()[0],
                        'supported_tasks': ['matrix_mult', 'calculation', 'nn_inference'],
                        'performance_score': random.randint(50, 100)
                    }
                }
                
                registration_json = json.dumps(registration)
                sock.sendall(registration_json.encode())
                self.connected = True
                logger.info(f"✅ Отправлена регистрация как '{self.name}'")
                return True
            else:
                logger.error(f"❌ Неожиданный ответ сервера: {response}")
                return False
            
        except socket.timeout:
            logger.error("❌ Таймаут при ожидании приветствия от сервера")
            return False
        except json.JSONDecodeError:
            logger.error("❌ Некорректный JSON от сервера")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка регистрации: {type(e).__name__}: {e}")
            return False
    
    def _send_heartbeat(self, sock: socket.socket):
        """Отправить heartbeat"""
        try:
            heartbeat = {
                'type': 'heartbeat',
                'worker_id': self.worker_id,
                'timestamp': time.time(),
                'name': self.name
            }
            heartbeat_json = json.dumps(heartbeat)
            sock.sendall(heartbeat_json.encode())
        except Exception as e:
            logger.warning(f"⚠️ Ошибка отправки heartbeat: {e}")
    
    def _process_task(self, task_type: str, task_data: Dict) -> Dict:
        """Обработать задачу"""
        start_time = time.time()
        
        try:
            if task_type == 'matrix_mult':
                size = task_data.get('size', 10)
                
                # Создаем матрицы
                matrix_a = MathUtils.random_matrix(size)
                matrix_b = MathUtils.random_matrix(size)
                
                # Выполняем умножение
                result = MathUtils.matrix_multiply(matrix_a, matrix_b)
                
                execution_time = time.time() - start_time
                
                return {
                    'status': 'success',
                    'task_type': task_type,
                    'matrix_size': size,
                    'execution_time': round(execution_time, 3),
                    'worker': self.name,
                    'worker_id': self.worker_id,
                    'checksum': hashlib.md5(str(result).encode()).hexdigest()[:8],
                    'timestamp': time.time(),
                    'performance': f"{round(1/execution_time if execution_time > 0 else 0, 1)} ops/sec"
                }
            
            elif task_type == 'calculation':
                # Простые вычисления
                numbers = task_data.get('numbers', 1000)
                operations = task_data.get('operations', ['sum', 'average', 'min', 'max'])
                
                # Генерируем случайные числа
                random_numbers = [random.random() for _ in range(numbers)]
                
                results = {}
                
                if 'sum' in operations:
                    results['sum'] = sum(random_numbers)
                if 'average' in operations:
                    results['average'] = sum(random_numbers) / len(random_numbers)
                if 'min' in operations:
                    results['min'] = min(random_numbers)
                if 'max' in operations:
                    results['max'] = max(random_numbers)
                
                execution_time = time.time() - start_time
                
                return {
                    'status': 'success',
                    'task_type': task_type,
                    'results': results,
                    'numbers_count': len(random_numbers),
                    'execution_time': round(execution_time, 3),
                    'worker': self.name,
                    'worker_id': self.worker_id,
                    'timestamp': time.time()
                }
            
            elif task_type == 'nn_inference':
                input_size = task_data.get('input_size', 10)
                inputs = [random.random() for _ in range(input_size)]
                
                # Создаем и запускаем нейросеть
                nn = SimpleNeuralNetwork(input_size=input_size)
                outputs = nn.predict(inputs)
                
                execution_time = time.time() - start_time
                
                return {
                    'status': 'success',
                    'task_type': task_type,
                    'input_size': input_size,
                    'outputs': [round(x, 4) for x in outputs],
                    'execution_time': round(execution_time, 3),
                    'worker': self.name,
                    'worker_id': self.worker_id,
                    'timestamp': time.time()
                }
            
            else:
                return {
                    'status': 'error',
                    'message': f'Неизвестный тип задачи: {task_type}',
                    'worker': self.name,
                    'worker_id': self.worker_id,
                    'timestamp': time.time()
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'error_type': type(e).__name__,
                'worker': self.name,
                'worker_id': self.worker_id,
                'timestamp': time.time()
            }
    
    def worker_loop(self, sock: socket.socket):
        """Основной цикл работы рабочего"""
        last_heartbeat = 0
        
        try:
            logger.info("🚀 Рабочий узел готов к выполнению задач!")
            logger.info("=" * 50)
            
            while self.running and self.connected:
                current_time = time.time()
                
                # Отправляем heartbeat каждые 20 секунд
                if current_time - last_heartbeat > 20:
                    self._send_heartbeat(sock)
                    last_heartbeat = current_time
                
                try:
                    # Проверяем наличие задач
                    sock.settimeout(2)
                    data = sock.recv(4096)
                    
                    if data:
                        raw_data = data.decode('utf-8', errors='ignore')
                        
                        # Извлекаем все JSON сообщения
                        messages = self._extract_json_messages(raw_data)
                        
                        for message in messages:
                            if message.get('type') == 'task':
                                task_id = message['task_id']
                                task_type = message['task_type']
                                task_data = message.get('data', {})
                                
                                logger.info(f"📥 Получена задача: {task_id} ({task_type})")
                                
                                # Обрабатываем задачу
                                result = self._process_task(task_type, task_data)
                                
                                # Отправляем результат
                                response = {
                                    'type': 'result',
                                    'task_id': task_id,
                                    'result': result,
                                    'timestamp': time.time()
                                }
                                
                                response_json = json.dumps(response)
                                sock.sendall(response_json.encode())
                                
                                if result['status'] == 'success':
                                    logger.info(f"✅ Задача {task_id} выполнена за {result.get('execution_time', 0):.3f} сек")
                                else:
                                    logger.warning(f"⚠️ Задача {task_id} завершилась с ошибкой: {result.get('message')}")
                            
                            elif message.get('type') == 'heartbeat_ack':
                                # Подтверждение heartbeat
                                pass
                        
                except socket.timeout:
                    continue
                except ConnectionResetError:
                    logger.error("❌ Соединение разорвано сервером")
                    self.connected = False
                    break
                except Exception as e:
                    logger.error(f"❌ Ошибка приема данных: {type(e).__name__}: {e}")
                    self.connected = False
                    break
                    
        except Exception as e:
            logger.error(f"❌ Ошибка в рабочем цикле: {type(e).__name__}: {e}")
            self.connected = False
        finally:
            try:
                sock.close()
            except:
                pass
    
    def _extract_json_messages(self, buffer: str) -> List[Dict]:
        """Извлечь все полные JSON сообщения из буфера"""
        messages = []
        start = 0
        depth = 0
        in_string = False
        escape = False
        
        for i, char in enumerate(buffer):
            if not in_string:
                if char == '{':
                    if depth == 0:
                        start = i
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        # Нашли полный JSON объект
                        try:
                            message = json.loads(buffer[start:i+1])
                            messages.append(message)
                        except json.JSONDecodeError:
                            # Пропускаем некорректный JSON
                            pass
                elif char == '"':
                    in_string = True
            else:
                if escape:
                    escape = False
                elif char == '\\':
                    escape = True
                elif char == '"':
                    in_string = False
        
        return messages
    
    def start(self):
        """Запуск рабочего узла"""
        self.running = True
        
        logger.info(f"👷 Запуск рабочего узла: {self.name}")
        logger.info(f"📡 Подключение к серверу: {self.server_host}:{self.server_port}")
        logger.info("=" * 50)
        
        while self.running:
            try:
                self.connection_attempts += 1
                
                if self.connection_attempts > self.max_connection_attempts:
                    logger.error(f"❌ Превышено максимальное количество попыток ({self.max_connection_attempts})")
                    break
                
                sock = self.safe_connect()
                
                if not sock:
                    logger.warning(f"⚠️ Повтор через {self.reconnect_delay} сек... (попытка {self.connection_attempts}/{self.max_connection_attempts})")
                    time.sleep(self.reconnect_delay)
                    self.reconnect_delay = min(self.reconnect_delay * 1.5, 60)
                    continue
                
                if not self.register_with_server(sock):
                    logger.warning("⚠️ Ошибка регистрации, переподключение...")
                    sock.close()
                    time.sleep(5)
                    continue
                
                # Сброс счетчика при успешном подключении
                self.connection_attempts = 0
                self.reconnect_delay = 5
                
                self.worker_loop(sock)
                
                if self.running and not self.connected:
                    logger.warning("⚠️ Потеряно соединение с сервером")
                    logger.info(f"🔌 Переподключение через {self.reconnect_delay} сек...")
                    time.sleep(self.reconnect_delay)
                    self.reconnect_delay = min(self.reconnect_delay * 1.5, 60)
                
            except KeyboardInterrupt:
                logger.info("👋 Получен сигнал завершения...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"❌ Критическая ошибка: {type(e).__name__}: {e}")
                time.sleep(10)
        
        logger.info("👷 Рабочий узел остановлен")

# ========== ГЛАВНАЯ ФУНКЦИЯ ==========
def main():
    parser = argparse.ArgumentParser(
        description="🚀 Децентрализованная AI сеть - Координатор и рабочие узлы",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--coordinator', action='store_true',
                       help='Запустить координатор сети')
    parser.add_argument('--worker', action='store_true',
                       help='Запустить рабочий узел')
    parser.add_argument('--host', default=None,
                       help='Адрес сервера (для рабочего) или хост (для координатора)')
    parser.add_argument('--port', type=int, default=8888,
                       help='Порт сервера (по умолчанию: 8888)')
    parser.add_argument('--web-port', type=int, default=8890,
                       help='Порт веб-интерфейса (по умолчанию: 8890)')
    parser.add_argument('--name', 
                       help='Имя рабочего узла')
    
    args = parser.parse_args()
    
    if args.coordinator:
        # Для координатора всегда используем 0.0.0.0 чтобы слушать на всех интерфейсах
        coordinator = NetworkCoordinator(
            host="0.0.0.0",  # Всегда слушаем на всех интерфейсах
            worker_port=args.port,
            web_port=args.web_port
        )
        coordinator.start()
    
    elif args.worker:
        if not args.host:
            print("❌ Для запуска рабочего узла необходимо указать --host")
            print("Пример: python ai_network.py --worker --host 185.185.142.113 --name 'MyPC'")
            return
        
        worker = WorkerNode(
            server_host=args.host,
            server_port=args.port,
            name=args.name
        )
        worker.start()
    
    else:
        print("=" * 70)
        print("🤖 ДЕЦЕНТРАЛИЗОВАННАЯ AI СЕТЬ v1.0")
        print("=" * 70)
        print()
        print("КОМАНДЫ:")
        print("  --coordinator           Запустить координатор сети")
        print("  --worker                Запустить рабочий узел")
        print()
        print("ПРИМЕРЫ:")
        print("  1. Запуск координатора:")
        print("     python ai_network.py --coordinator --port 8888 --web-port 8890")
        print()
        print("  2. Подключение рабочего:")
        print("     python ai_network.py --worker --host 185.185.142.113 --name 'MyPC'")
        print()
        print("📡 Публичный API:")
        print(f"    • Проверка: GET http://185.185.142.113:8890/api/health")
        print(f"    • Статус: GET http://185.185.142.113:8890/api/status")
        print(f"    • Задачи: GET http://185.185.142.113:8890/api/tasks")
        print(f"    • Отправить: POST http://185.185.142.113:8890/api/submit")
        print("=" * 70)
        
        choice = input("\nВыберите режим (1 - координатор, 2 - рабочий, Enter - выход): ")
        
        if choice == '1':
            host = input(f"Хост координатора [0.0.0.0]: ") or "0.0.0.0"
            port = input("Порт для рабочих [8888]: ") or "8888"
            web_port = input("Порт веб-интерфейса [8890]: ") or "8890"
            
            coordinator = NetworkCoordinator(
                host=host,
                worker_port=int(port),
                web_port=int(web_port)
            )
            coordinator.start()
        
        elif choice == '2':
            host = input("Адрес сервера координатора: ")
            if not host:
                print("❌ Необходимо указать адрес сервера")
                return
            
            name = input(f"Имя рабочего [Worker_{random.randint(1000, 9999)}]: ") or f"Worker_{random.randint(1000, 9999)}"
            
            worker = WorkerNode(
                server_host=host,
                server_port=8888,
                name=name
            )
            worker.start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Программа завершена")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
