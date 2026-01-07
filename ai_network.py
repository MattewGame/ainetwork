#!/usr/bin/env python3
"""
🚀 Децентрализованная AI сеть MVP - Универсальная версия
Поддержка IPv4/IPv6, автоматическое определение адресов
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
from datetime import datetime
from typing import Dict, List, Optional, Any

# Веб-интерфейс
try:
    from flask import Flask, render_template_string, jsonify, request
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️ Flask не установлен. Установите: pip install flask")
    sys.exit(1)

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
        sock = socket.socket(socket.AF_INET6 if socket.has_ipv6 else socket.AF_INET, 
                           socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if socket.has_ipv6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)  # Принимать и IPv4, и IPv6
        sock.settimeout(10)
        return sock

# ========== КООРДИНАТОР СЕТИ ==========
class NetworkCoordinator:
    """Координатор децентрализованной сети"""
    
    def __init__(self, host: str = None, worker_port: int = 8888, web_port: int = 8890):
        # Автоматически определяем лучший хост если не указан
        self.host = host if host else NetworkUtils.get_best_public_ip()
        self.worker_port = worker_port
        self.web_port = web_port
        
        # Данные сети
        self.workers: Dict[str, Dict] = {}
        self.tasks: Dict[str, Dict] = {}
        self.task_queue: List[str] = []
        
        # Синхронизация
        self.lock = threading.RLock()
        self.running = False
        
        # Веб-сервер
        self.app = Flask(__name__)
        self._setup_web_routes()
        
        logger.info(f"Инициализация координатора на {self.host}")
    
    def _setup_web_routes(self):
        """Настройка маршрутов веб-сервера"""
        
        @self.app.route('/')
        def index():
            return self._get_web_interface()
        
        @self.app.route('/api/status', methods=['GET'])
        def api_status():
            return jsonify({
                'status': 'running',
                'coordinator': {
                    'host': self.host,
                    'worker_port': self.worker_port,
                    'web_port': self.web_port,
                    'uptime': getattr(self, 'start_time', time.time())
                }
            })
        
        @self.app.route('/api/stats', methods=['GET'])
        def api_stats():
            with self.lock:
                stats = self._get_stats()
            return jsonify(stats)
        
        @self.app.route('/api/tasks', methods=['GET'])
        def api_tasks():
            with self.lock:
                return jsonify({
                    'tasks': list(self.tasks.values()),
                    'queue': self.task_queue
                })
        
        @self.app.route('/api/submit', methods=['POST'])
        def api_submit():
            try:
                data = request.json or {}
                task_type = data.get('type', 'matrix_mult')
                task_data = data.get('data', {})
                
                task_id = self._create_task(task_type, task_data)
                
                return jsonify({
                    'status': 'success',
                    'task_id': task_id,
                    'message': 'Задача создана'
                })
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 400
        
        @self.app.route('/api/workers', methods=['GET'])
        def api_workers():
            with self.lock:
                workers = []
                for worker_id, worker in self.workers.items():
                    workers.append({
                        'id': worker_id[:8],
                        'name': worker.get('name', 'unknown'),
                        'address': f"{worker['addr'][0]}:{worker['addr'][1]}",
                        'status': worker.get('status', 'unknown'),
                        'last_seen': worker.get('last_seen', time.time()),
                        'current_task': worker.get('current_task')
                    })
                
                return jsonify({'workers': workers})
    
    def _get_web_interface(self):
        """Генерация веб-интерфейса"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>🤖 AI Network - Децентрализованные вычисления</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    color: #333;
                    padding: 20px;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 15px;
                    padding: 30px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                }}
                header {{
                    text-align: center;
                    margin-bottom: 40px;
                    padding-bottom: 20px;
                    border-bottom: 3px solid #667eea;
                }}
                h1 {{
                    color: #4a5568;
                    font-size: 2.8em;
                    margin-bottom: 10px;
                }}
                .subtitle {{
                    color: #718096;
                    font-size: 1.2em;
                }}
                .info-box {{
                    background: #f7fafc;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                    border-left: 5px solid #4299e1;
                }}
                .grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .card {{
                    background: white;
                    padding: 25px;
                    border-radius: 10px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.05);
                    transition: transform 0.3s ease;
                }}
                .card:hover {{ transform: translateY(-5px); }}
                .card h3 {{
                    color: #4a5568;
                    margin-bottom: 15px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                .stat-grid {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 15px;
                }}
                .stat-item {{
                    text-align: center;
                    padding: 15px;
                    background: #edf2f7;
                    border-radius: 8px;
                }}
                .stat-number {{
                    font-size: 2em;
                    font-weight: bold;
                    color: #4299e1;
                }}
                .btn {{
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px 25px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: bold;
                    border: none;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }}
                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 7px 20px rgba(0,0,0,0.15);
                }}
                .worker-list, .task-list {{
                    list-style: none;
                }}
                .worker-item, .task-item {{
                    padding: 15px;
                    margin: 10px 0;
                    background: #f7fafc;
                    border-radius: 8px;
                    border-left: 4px solid #4299e1;
                }}
                .task-item.completed {{ border-left-color: #48bb78; }}
                .task-item.running {{ border-left-color: #ed8936; }}
                .task-item.failed {{ border-left-color: #f56565; }}
                .status {{
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 0.9em;
                    font-weight: bold;
                    margin-left: 10px;
                }}
                .status-connected {{ background: #c6f6d5; color: #22543d; }}
                .status-disconnected {{ background: #fed7d7; color: #c53030; }}
                .status-pending {{ background: #feebc8; color: #b7791f; }}
                .refresh-btn {{
                    background: none;
                    border: none;
                    color: #667eea;
                    cursor: pointer;
                    font-size: 1.2em;
                    float: right;
                }}
                code {{
                    background: #2d3748;
                    color: #e2e8f0;
                    padding: 10px 15px;
                    border-radius: 6px;
                    display: block;
                    margin: 10px 0;
                    font-family: 'Courier New', monospace;
                }}
                @media (max-width: 768px) {{
                    .container {{ padding: 15px; }}
                    h1 {{ font-size: 2em; }}
                    .grid {{ grid-template-columns: 1fr; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>🤖 AI Network</h1>
                    <p class="subtitle">Децентрализованные вычисления в реальном времени</p>
                </header>
                
                <div class="info-box">
                    <h3>📡 Информация о сервере</h3>
                    <p><strong>Адрес сервера:</strong> {self.host}</p>
                    <p><strong>Порт для рабочих:</strong> {self.worker_port}</p>
                    <p><strong>Веб-порт:</strong> {self.web_port}</p>
                    <p><strong>Время запуска:</strong> <span id="uptime">только что</span></p>
                </div>
                
                <div class="grid">
                    <div class="card">
                        <h3>📊 Статистика сети</h3>
                        <div class="stat-grid" id="stats">
                            <!-- Динамически заполняется JavaScript -->
                        </div>
                        <button class="refresh-btn" onclick="loadStats()">🔄</button>
                    </div>
                    
                    <div class="card">
                        <h3>👷 Рабочие узлы</h3>
                        <div id="workers-container">
                            <p>Загрузка...</p>
                        </div>
                        <button class="refresh-btn" onclick="loadWorkers()">🔄</button>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📤 Отправить задачу</h3>
                    <form onsubmit="submitTask(event)">
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">Тип задачи:</label>
                            <select id="taskType" style="width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0;">
                                <option value="matrix_mult">Умножение матриц</option>
                                <option value="calculation">Математические вычисления</option>
                                <option value="nn_inference">Инференс нейросети</option>
                            </select>
                        </div>
                        <div style="margin-bottom: 20px;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">Параметры (JSON):</label>
                            <textarea id="taskData" style="width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0; height: 80px;" 
                                      placeholder='{{"size": 10}}'></textarea>
                        </div>
                        <button type="submit" class="btn">🚀 Отправить задачу</button>
                    </form>
                </div>
                
                <div class="card">
                    <h3>📋 Активные задачи</h3>
                    <div id="tasks-container">
                        <p>Загрузка...</p>
                    </div>
                    <button class="refresh-btn" onclick="loadTasks()">🔄</button>
                </div>
                
                <div class="card">
                    <h3>🔗 Как подключиться</h3>
                    <p>Для подключения рабочего узла выполните:</p>
                    <code>python ai_network.py --worker --host {self.host} --port {self.worker_port} --name "Ваш_компьютер"</code>
                    <p>Или используйте упрощенный скрипт:</p>
                    <code id="connect-command">python -c "import socket;s=socket.socket();s.connect(('{self.host}',{self.worker_port}));print('✅ Подключено!')"</code>
                </div>
            </div>
            
            <script>
                const API_BASE = window.location.origin;
                
                async function loadStats() {{
                    try {{
                        const response = await fetch(API_BASE + '/api/stats');
                        const data = await response.json();
                        
                        document.getElementById('stats').innerHTML = `
                            <div class="stat-item">
                                <div class="stat-number">${{data.workers_count}}</div>
                                <div>Рабочих узлов</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">${{data.tasks_pending}}</div>
                                <div>В очереди</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">${{data.tasks_running}}</div>
                                <div>Выполняется</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">${{data.tasks_completed}}</div>
                                <div>Завершено</div>
                            </div>
                        `;
                    }} catch (error) {{
                        console.error('Ошибка загрузки статистики:', error);
                    }}
                }}
                
                async function loadWorkers() {{
                    try {{
                        const response = await fetch(API_BASE + '/api/workers');
                        const data = await response.json();
                        
                        const container = document.getElementById('workers-container');
                        if (data.workers && data.workers.length > 0) {{
                            container.innerHTML = data.workers.map(worker => `
                                <div class="worker-item">
                                    <strong>${{worker.name}}</strong>
                                    <span class="status status-${{worker.status === 'connected' ? 'connected' : 'disconnected'}}">
                                        ${{worker.status === 'connected' ? '✅ Подключен' : '❌ Отключен'}}
                                    </span>
                                    <div style="margin-top: 5px; font-size: 0.9em; color: #718096;">
                                        ${{worker.address}} • Задача: ${{worker.current_task || 'нет'}}
                                    </div>
                                </div>
                            `).join('');
                        }} else {{
                            container.innerHTML = '<p>Нет подключенных рабочих узлов</p>';
                        }}
                    }} catch (error) {{
                        console.error('Ошибка загрузки рабочих:', error);
                    }}
                }}
                
                async function loadTasks() {{
                    try {{
                        const response = await fetch(API_BASE + '/api/tasks');
                        const data = await response.json();
                        
                        const container = document.getElementById('tasks-container');
                        if (data.tasks && data.tasks.length > 0) {{
                            container.innerHTML = data.tasks.slice(-10).reverse().map(task => `
                                <div class="task-item ${{task.status}}">
                                    <strong>${{task.id?.slice(0, 8) || 'unknown'}}</strong>
                                    <span class="status status-${{task.status}}">
                                        ${{task.status === 'completed' ? '✅' : 
                                           task.status === 'running' ? '⚡' : 
                                           task.status === 'failed' ? '❌' : '⏳'}}
                                        ${{task.status}}
                                    </span>
                                    <div style="margin-top: 5px; font-size: 0.9em;">
                                        Тип: ${{task.type}} • Рабочий: ${{task.worker || 'не назначен'}}
                                    </div>
                                </div>
                            `).join('');
                        }} else {{
                            container.innerHTML = '<p>Нет активных задач</p>';
                        }}
                    }} catch (error) {{
                        console.error('Ошибка загрузки задач:', error);
                    }}
                }}
                
                async function submitTask(event) {{
                    event.preventDefault();
                    
                    const taskType = document.getElementById('taskType').value;
                    let taskData = {{}};
                    
                    try {{
                        const dataInput = document.getElementById('taskData').value;
                        taskData = dataInput ? JSON.parse(dataInput) : {{}};
                    }} catch (e) {{
                        alert('Ошибка в JSON данных задачи');
                        return;
                    }}
                    
                    try {{
                        const response = await fetch(API_BASE + '/api/submit', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{
                                type: taskType,
                                data: taskData
                            }})
                        }});
                        
                        const result = await response.json();
                        
                        if (result.status === 'success') {{
                            alert(`✅ Задача отправлена! ID: ${{result.task_id}}`);
                            loadStats();
                            loadTasks();
                        }} else {{
                            alert(`❌ Ошибка: ${{result.message}}`);
                        }}
                    }} catch (error) {{
                        alert('Ошибка подключения к серверу');
                    }}
                }}
                
                // Автообновление
                setInterval(() => {{
                    loadStats();
                    loadWorkers();
                    loadTasks();
                }}, 3000);
                
                // Первоначальная загрузка
                document.addEventListener('DOMContentLoaded', () => {{
                    loadStats();
                    loadWorkers();
                    loadTasks();
                    
                    // Обновляем uptime
                    const startTime = Date.now();
                    function updateUptime() {{
                        const uptime = Date.now() - startTime;
                        const hours = Math.floor(uptime / 3600000);
                        const minutes = Math.floor((uptime % 3600000) / 60000);
                        const seconds = Math.floor((uptime % 60000) / 1000);
                        document.getElementById('uptime').textContent = 
                            `${{hours.toString().padStart(2, '0')}}:${{minutes.toString().padStart(2, '0')}}:${{seconds.toString().padStart(2, '0')}}`;
                    }}
                    setInterval(updateUptime, 1000);
                    updateUptime();
                }});
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
            
            connected_workers = len([w for w in self.workers.values() if w.get('status') == 'connected'])
            
            return {
                'workers_count': connected_workers,
                'tasks_total': len(self.tasks),
                'tasks_pending': tasks_pending,
                'tasks_running': tasks_running,
                'tasks_completed': tasks_completed,
                'queue_length': len(self.task_queue),
                'timestamp': time.time()
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
                'result': None
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
                'capabilities': {}
            }
        
        try:
            # Устанавливаем таймаут
            conn.settimeout(30)
            
            # Отправляем приветственное сообщение
            welcome_msg = {
                'type': 'welcome',
                'worker_id': worker_id,
                'message': 'Добро пожаловать в AI Network!',
                'timestamp': time.time()
            }
            conn.sendall(json.dumps(welcome_msg).encode())
            
            # Основной цикл обработки
            while self.running:
                try:
                    # Получаем данные от рабочего
                    data = conn.recv(4096)
                    
                    if not data:
                        logger.info(f"Рабочий {worker_id} отключился")
                        break
                    
                    try:
                        message = json.loads(data.decode('utf-8'))
                        
                        if message.get('type') == 'heartbeat':
                            # Обновляем время последней активности
                            with self.lock:
                                if worker_id in self.workers:
                                    self.workers[worker_id]['last_seen'] = time.time()
                            
                            # Отправляем подтверждение
                            ack = {'type': 'heartbeat_ack', 'timestamp': time.time()}
                            conn.sendall(json.dumps(ack).encode())
                            
                        elif message.get('type') == 'capabilities':
                            # Сохраняем возможности рабочего
                            with self.lock:
                                if worker_id in self.workers:
                                    self.workers[worker_id]['capabilities'] = message.get('capabilities', {})
                                    self.workers[worker_id]['name'] = message.get('name', self.workers[worker_id]['name'])
                            
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
                                        logger.info(f"Задача {task_id} успешно выполнена")
                                    else:
                                        self.tasks[task_id]['status'] = 'failed'
                                        self.tasks[task_id]['result'] = result
                                        logger.warning(f"Задача {task_id} завершилась с ошибкой")
                            
                            # Пробуем назначить следующую задачу
                            self._assign_tasks()
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Некорректный JSON от рабочего {worker_id}")
                    
                except socket.timeout:
                    # Таймаут - нормальная ситуация
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
            # Удаляем рабочего
            self._remove_worker(worker_id)
            try:
                conn.close()
            except:
                pass
    
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
            server.bind((self.host, self.worker_port))
            server.listen(10)
            
            logger.info(f"Сервер для рабочих запущен на {self.host}:{self.worker_port}")
            
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
            self.running = False
    
    def start(self):
        """Запуск координатора"""
        self.running = True
        self.start_time = time.time()
        
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК AI NETWORK COORDINATOR")
        logger.info("=" * 60)
        logger.info(f"🌐 Веб-интерфейс: http://{self.host}:{self.web_port}")
        logger.info(f"📡 Порт для рабочих: {self.worker_port}")
        logger.info(f"🔗 Адрес для подключения: {self.host}:{self.worker_port}")
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
            # Запускаем веб-сервер
            import warnings
            warnings.filterwarnings("ignore", message=".*Werkzeug.*")
            
            logger.info("✅ Система запущена и готова к работе!")
            logger.info("👷 Ожидание подключения рабочих узлов...")
            
            self.app.run(
                host=self.host,
                port=self.web_port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
            
        except KeyboardInterrupt:
            logger.info("Получен сигнал завершения...")
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
    
    def connect(self) -> Optional[socket.socket]:
        """Подключиться к координатору"""
        try:
            sock = NetworkUtils.create_socket()
            sock.settimeout(10)
            
            logger.info(f"Подключение к {self.server_host}:{self.server_port}...")
            sock.connect((self.server_host, self.server_port))
            
            # Устанавливаем таймаут после подключения
            sock.settimeout(300)
            
            # Регистрируемся
            registration = {
                'type': 'capabilities',
                'name': self.name,
                'timestamp': time.time(),
                'capabilities': {
                    'cpu_cores': os.cpu_count() or 1,
                    'platform': sys.platform,
                    'python_version': sys.version.split()[0],
                    'supported_tasks': ['matrix_mult', 'calculation', 'nn_inference']
                }
            }
            
            sock.sendall(json.dumps(registration).encode())
            
            # Ждем ответ
            data = sock.recv(4096)
            if data:
                response = json.loads(data.decode())
                if response.get('type') == 'welcome':
                    self.worker_id = response.get('worker_id')
                    logger.info(f"✅ {response.get('message')}")
                    logger.info(f"🆔 Ваш ID: {self.worker_id}")
                    self.connected = True
                    return sock
            
            return None
            
        except socket.timeout:
            logger.error("Таймаут подключения")
            return None
        except ConnectionRefusedError:
            logger.error("Не удалось подключиться. Проверьте адрес сервера.")
            return None
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return None
    
    def _send_heartbeat(self, sock: socket.socket):
        """Отправить heartbeat"""
        try:
            heartbeat = {
                'type': 'heartbeat',
                'worker_id': self.worker_id,
                'timestamp': time.time()
            }
            sock.sendall(json.dumps(heartbeat).encode())
        except:
            pass
    
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
                    'checksum': hashlib.md5(str(result).encode()).hexdigest()[:8],
                    'timestamp': time.time()
                }
            
            elif task_type == 'calculation':
                # Простые вычисления
                numbers = task_data.get('numbers', [random.random() for _ in range(100)])
                
                operations = task_data.get('operations', ['sum', 'average', 'min', 'max'])
                results = {}
                
                if 'sum' in operations:
                    results['sum'] = sum(numbers)
                if 'average' in operations:
                    results['average'] = sum(numbers) / len(numbers)
                if 'min' in operations:
                    results['min'] = min(numbers)
                if 'max' in operations:
                    results['max'] = max(numbers)
                
                execution_time = time.time() - start_time
                
                return {
                    'status': 'success',
                    'task_type': task_type,
                    'results': results,
                    'numbers_count': len(numbers),
                    'execution_time': round(execution_time, 3),
                    'worker': self.name,
                    'timestamp': time.time()
                }
            
            elif task_type == 'nn_inference':
                input_size = task_data.get('input_size', 5)
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
                    'timestamp': time.time()
                }
            
            else:
                return {
                    'status': 'error',
                    'message': f'Неизвестный тип задачи: {task_type}',
                    'worker': self.name,
                    'timestamp': time.time()
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'worker': self.name,
                'timestamp': time.time()
            }
    
    def start(self):
        """Запуск рабочего узла"""
        self.running = True
        
        logger.info(f"👷 Запуск рабочего узла: {self.name}")
        logger.info(f"📡 Сервер: {self.server_host}:{self.server_port}")
        
        last_heartbeat = 0
        
        while self.running:
            sock = self.connect()
            
            if not sock:
                logger.warning("Повторная попытка через 10 секунд...")
                time.sleep(10)
                continue
            
            try:
                logger.info("🚀 Рабочий узел готов к выполнению задач!")
                
                while self.running and self.connected:
                    current_time = time.time()
                    
                    # Отправляем heartbeat каждые 20 секунд
                    if current_time - last_heartbeat > 20:
                        self._send_heartbeat(sock)
                        last_heartbeat = current_time
                    
                    try:
                        # Проверяем наличие задач
                        sock.settimeout(1)
                        data = sock.recv(4096)
                        
                        if data:
                            try:
                                message = json.loads(data.decode('utf-8'))
                                
                                if message.get('type') == 'task':
                                    task_id = message['task_id']
                                    task_type = message['task_type']
                                    task_data = message.get('data', {})
                                    
                                    logger.info(f"📥 Получена задача: {task_id}")
                                    
                                    # Обрабатываем задачу
                                    result = self._process_task(task_type, task_data)
                                    
                                    # Отправляем результат
                                    response = {
                                        'type': 'result',
                                        'task_id': task_id,
                                        'result': result,
                                        'timestamp': time.time()
                                    }
                                    
                                    sock.sendall(json.dumps(response).encode())
                                    logger.info(f"✅ Задача {task_id} выполнена за {result.get('execution_time', 0):.3f} сек")
                                    
                                elif message.get('type') == 'heartbeat_ack':
                                    # Подтверждение heartbeat
                                    pass
                                    
                            except json.JSONDecodeError:
                                logger.warning("Некорректный JSON от сервера")
                        
                    except socket.timeout:
                        continue
                    except ConnectionResetError:
                        logger.error("Соединение разорвано сервером")
                        self.connected = False
                        break
                    except Exception as e:
                        logger.error(f"Ошибка приема данных: {e}")
                        self.connected = False
                        break
                
                sock.close()
                self.connected = False
                
                if self.running:
                    logger.warning("Переподключение через 5 секунд...")
                    time.sleep(5)
                
            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {e}")
                time.sleep(5)

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
        # Запуск координатора
        coordinator = NetworkCoordinator(
            host=args.host,
            worker_port=args.port,
            web_port=args.web_port
        )
        coordinator.start()
    
    elif args.worker:
        if not args.host:
            print("❌ Для запуска рабочего узла необходимо указать --host")
            print("Пример: python ai_network.py --worker --host 185.185.142.113 --name 'MyPC'")
            return
        
        # Запуск рабочего узла
        worker = WorkerNode(
            server_host=args.host,
            server_port=args.port,
            name=args.name
        )
        worker.start()
    
    else:
        # Информационный вывод
        print("=" * 70)
        print("🤖 ДЕЦЕНТРАЛИЗОВАННАЯ AI СЕТЬ")
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
        print("  3. Указать свой хост:")
        print("     python ai_network.py --coordinator --host 0.0.0.0")
        print("=" * 70)
        
        # Автоматический выбор режима
        choice = input("\nВыберите режим (1 - координатор, 2 - рабочий, Enter - выход): ")
        
        if choice == '1':
            host = input(f"Хост координатора [{NetworkUtils.get_best_public_ip()}]: ") or NetworkUtils.get_best_public_ip()
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
