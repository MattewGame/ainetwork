#!/usr/bin/env python3
"""
Децентрализованная AI сеть MVP для VPS
Исправленная версия с устойчивым соединением
"""

import socket
import threading
import json
import time
import random
import math
import hashlib
from datetime import datetime
import logging
import argparse
import sys
import os
import uuid

# Веб-интерфейс
from flask import Flask, render_template_string, jsonify, request

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AI-Network-VPS")

# ========== Упрощенные утилиты ==========
class MathUtils:
    @staticmethod
    def random_matrix(size):
        """Создать случайную матрицу"""
        return [[random.random() for _ in range(size)] for _ in range(size)]
    
    @staticmethod
    def matrix_multiply(a, b):
        """Умножение матриц"""
        n = len(a)
        result = [[0 for _ in range(n)] for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                for k in range(n):
                    result[i][j] += a[i][k] * b[k][j]
        
        return result
    
    @staticmethod
    def sigmoid(x):
        """Сигмоидная функция"""
        return 1 / (1 + math.exp(-x))

# ========== Простая нейронная сеть ==========
class SimpleNeuralNetwork:
    def __init__(self, input_size=3, hidden_size=4, output_size=2):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        # Инициализация весов
        self.w1 = [[random.random() - 0.5 for _ in range(hidden_size)] 
                   for _ in range(input_size)]
        self.b1 = [0.0] * hidden_size
        
        self.w2 = [[random.random() - 0.5 for _ in range(output_size)] 
                   for _ in range(hidden_size)]
        self.b2 = [0.0] * output_size
    
    def predict(self, x):
        """Предсказание"""
        # Скрытый слой
        hidden = [0.0] * self.hidden_size
        for i in range(self.hidden_size):
            weighted_sum = 0.0
            for j in range(self.input_size):
                weighted_sum += x[j] * self.w1[j][i]
            hidden[i] = MathUtils.sigmoid(weighted_sum + self.b1[i])
        
        # Выходной слой
        output = [0.0] * self.output_size
        for i in range(self.output_size):
            weighted_sum = 0.0
            for j in range(self.hidden_size):
                weighted_sum += hidden[j] * self.w2[j][i]
            output[i] = MathUtils.sigmoid(weighted_sum + self.b2[i])
        
        return output

# ========== Координатор для VPS ==========
class CoordinatorVPS:
    def __init__(self, host='0.0.0.0', worker_port=8888, web_port=8890):
        self.host = host
        self.worker_port = worker_port
        self.web_port = web_port
        
        self.workers = {}  # ID -> {'conn': socket, 'addr': tuple, 'last_seen': datetime}
        self.tasks = {}  # task_id -> {'type': str, 'data': dict, 'status': str, 'result': any, 'worker': str}
        self.task_queue = []  # [task_id, task_id, ...]
        
        self.lock = threading.RLock()
        self.running = True
        
        # Flask app
        self.app = Flask(__name__)
        self.setup_routes()
    
    def setup_routes(self):
        """Настройка маршрутов Flask"""
        
        @self.app.route('/')
        def index():
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>AI Network - VPS</title>
                <meta charset="utf-8">
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                        background: #f5f5f5;
                    }
                    .header {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 30px;
                        border-radius: 10px;
                        margin-bottom: 20px;
                        text-align: center;
                    }
                    .stats {
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 15px;
                        margin-bottom: 20px;
                    }
                    .stat-card {
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        text-align: center;
                    }
                    .stat-number {
                        font-size: 2em;
                        font-weight: bold;
                        color: #667eea;
                    }
                    .panel {
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        margin-bottom: 20px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    .btn {
                        background: #667eea;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 5px;
                        cursor: pointer;
                        font-size: 16px;
                    }
                    .btn:hover {
                        background: #764ba2;
                    }
                    .task {
                        background: #f8f9fa;
                        padding: 15px;
                        margin: 10px 0;
                        border-radius: 5px;
                        border-left: 4px solid #667eea;
                    }
                    .task.completed { border-left-color: #28a745; }
                    .task.running { border-left-color: #ffc107; }
                    .task.failed { border-left-color: #dc3545; }
                    .status {
                        display: inline-block;
                        padding: 3px 10px;
                        border-radius: 15px;
                        font-size: 0.8em;
                        font-weight: bold;
                    }
                    .status-pending { background: #ffc107; color: #333; }
                    .status-running { background: #17a2b8; color: white; }
                    .status-completed { background: #28a745; color: white; }
                    .status-failed { background: #dc3545; color: white; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🚀 AI Network на VPS</h1>
                    <p>Децентрализованные вычисления на вашем сервере</p>
                </div>
                
                <div class="stats" id="stats"></div>
                
                <div class="panel">
                    <h2>📤 Отправить задачу</h2>
                    <form onsubmit="submitTask(event)">
                        <div>
                            <label>Тип задачи:</label>
                            <select id="taskType" style="width: 200px; padding: 8px; margin: 10px;">
                                <option value="matrix_mult">Умножение матриц</option>
                                <option value="calculation">Вычисления</option>
                                <option value="nn_inference">Нейронная сеть</option>
                            </select>
                        </div>
                        <div>
                            <label>Размер матрицы:</label>
                            <input type="number" id="matrixSize" value="10" min="5" max="50" 
                                   style="width: 100px; padding: 8px; margin: 10px;">
                        </div>
                        <button type="submit" class="btn">Отправить</button>
                    </form>
                </div>
                
                <div class="panel">
                    <h2>👷 Активные рабочие</h2>
                    <div id="workers"></div>
                </div>
                
                <div class="panel">
                    <h2>📋 Последние задачи</h2>
                    <div id="tasks"></div>
                </div>
                
                <div class="panel">
                    <h2>🔗 Как подключиться</h2>
                    <p>Для подключения рабочих узлов выполните:</p>
                    <code style="background: #f8f9fa; padding: 10px; display: block; border-radius: 5px;">
                        python3 ai_network.py --worker --host {{ server_ip }} --port 8888 --name "Ваше_Имя"
                    </code>
                    <p>Где {{ server_ip }} - IP адрес этого сервера</p>
                </div>
                
                <script>
                    const API_URL = window.location.origin + '/api';
                    
                    async function loadStats() {
                        try {
                            const res = await fetch(API_URL + '/stats');
                            const data = await res.json();
                            
                            // Обновляем статистику
                            document.getElementById('stats').innerHTML = `
                                <div class="stat-card">
                                    <div class="stat-number">${data.workers_count}</div>
                                    <div>Рабочих</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-number">${data.pending_tasks}</div>
                                    <div>В очереди</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-number">${data.running_tasks}</div>
                                    <div>Выполняется</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-number">${data.completed_tasks}</div>
                                    <div>Завершено</div>
                                </div>
                            `;
                            
                            // Обновляем рабочих
                            const workersDiv = document.getElementById('workers');
                            if (data.workers && data.workers.length > 0) {
                                workersDiv.innerHTML = data.workers.map(w => `
                                    <div style="background: #e9ecef; padding: 10px; margin: 5px 0; border-radius: 5px;">
                                        ${w.addr} - ${w.status} (был ${w.last_seen})
                                    </div>
                                `).join('');
                            } else {
                                workersDiv.innerHTML = '<p>Нет активных рабочих</p>';
                            }
                            
                            // Обновляем задачи
                            const tasksDiv = document.getElementById('tasks');
                            if (data.recent_tasks && data.recent_tasks.length > 0) {
                                tasksDiv.innerHTML = data.recent_tasks.map(t => `
                                    <div class="task ${t.status}">
                                        <strong>${t.task_id}</strong>
                                        <span class="status status-${t.status}">
                                            ${t.status === 'pending' ? '⏳' : 
                                             t.status === 'running' ? '⚡' : 
                                             t.status === 'completed' ? '✅' : '❌'}
                                            ${t.status}
                                        </span><br>
                                        Тип: ${t.type}<br>
                                        ${t.result ? `Результат: ${JSON.stringify(t.result).substring(0, 50)}...` : ''}
                                    </div>
                                `).join('');
                            } else {
                                tasksDiv.innerHTML = '<p>Нет задач</p>';
                            }
                            
                            // Обновляем IP в инструкции
                            document.body.innerHTML = document.body.innerHTML.replace(
                                '{{ server_ip }}',
                                window.location.hostname
                            );
                            
                        } catch (error) {
                            console.error('Ошибка загрузки:', error);
                        }
                    }
                    
                    async function submitTask(event) {
                        event.preventDefault();
                        
                        const taskType = document.getElementById('taskType').value;
                        const size = parseInt(document.getElementById('matrixSize').value);
                        
                        const taskData = { size: size };
                        
                        try {
                            const res = await fetch(API_URL + '/submit', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    task_type: taskType,
                                    data: taskData
                                })
                            });
                            
                            const result = await res.json();
                            if (result.status === 'success') {
                                alert(`Задача отправлена! ID: ${result.task_id}`);
                                loadStats();
                            } else {
                                alert(`Ошибка: ${result.message}`);
                            }
                        } catch (error) {
                            alert('Ошибка подключения к серверу');
                        }
                    }
                    
                    // Автообновление каждые 3 секунды
                    setInterval(loadStats, 3000);
                    
                    // Первоначальная загрузка
                    loadStats();
                </script>
            </body>
            </html>
            """)
        
        @self.app.route('/api/stats', methods=['GET'])
        def api_stats():
            with self.lock:
                workers_list = []
                for worker_id, worker in self.workers.items():
                    workers_list.append({
                        'id': worker_id,
                        'addr': f"{worker['addr'][0]}:{worker['addr'][1]}",
                        'status': worker.get('status', 'active'),
                        'last_seen': worker['last_seen'].strftime('%H:%M:%S')
                    })
                
                pending = len([t for t in self.tasks.values() if t['status'] == 'pending'])
                running = len([t for t in self.tasks.values() if t['status'] == 'running'])
                completed = len([t for t in self.tasks.values() if t['status'] == 'completed'])
                failed = len([t for t in self.tasks.values() if t['status'] == 'failed'])
                
                # Последние 10 задач
                recent_tasks = []
                for task_id, task in list(self.tasks.items())[-10:]:
                    recent_tasks.append({
                        'task_id': task_id,
                        'type': task['type'],
                        'status': task['status'],
                        'result': task.get('result'),
                        'created': task.get('created')
                    })
                
                return jsonify({
                    'workers_count': len(self.workers),
                    'workers': workers_list,
                    'pending_tasks': pending,
                    'running_tasks': running,
                    'completed_tasks': completed,
                    'failed_tasks': failed,
                    'total_tasks': len(self.tasks),
                    'recent_tasks': recent_tasks[::-1]  # Новые сверху
                })
        
        @self.app.route('/api/submit', methods=['POST'])
        def api_submit():
            try:
                data = request.json
                task_type = data.get('task_type', 'matrix_mult')
                task_data = data.get('data', {})
                
                task_id = str(uuid.uuid4())[:8]
                
                with self.lock:
                    self.tasks[task_id] = {
                        'type': task_type,
                        'data': task_data,
                        'status': 'pending',
                        'created': datetime.now().strftime('%H:%M:%S'),
                        'worker': None,
                        'result': None
                    }
                    self.task_queue.append(task_id)
                
                # Пытаемся сразу назначить задачу
                self._assign_tasks()
                
                return jsonify({
                    'status': 'success',
                    'task_id': task_id,
                    'message': 'Задача поставлена в очередь'
                })
                
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 400
        
        @self.app.route('/api/tasks', methods=['GET'])
        def api_tasks():
            with self.lock:
                return jsonify({
                    'tasks': list(self.tasks.values()),
                    'queue_length': len(self.task_queue)
                })
    
    def start(self):
        """Запуск координатора на VPS"""
        logger.info(f"🚀 Запуск AI Network на VPS")
        logger.info(f"📡 Порт для рабочих: {self.worker_port}")
        logger.info(f"🌐 Веб-интерфейс: http://{self.host if self.host != '0.0.0.0' else 'localhost'}:{self.web_port}")
        logger.info(f"🔗 IP сервера: {self._get_public_ip()}")
        
        # Запускаем сервер для рабочих
        worker_server_thread = threading.Thread(target=self._run_worker_server, daemon=True)
        worker_server_thread.start()
        
        # Запускаем обработчик задач
        task_processor_thread = threading.Thread(target=self._task_processor, daemon=True)
        task_processor_thread.start()
        
        # Запускаем очистку неактивных рабочих
        cleaner_thread = threading.Thread(target=self._cleanup_workers, daemon=True)
        cleaner_thread.start()
        
        # Запускаем heartbeat отправку
        heartbeat_thread = threading.Thread(target=self._send_heartbeats, daemon=True)
        heartbeat_thread.start()
        
        logger.info("✅ Система запущена!")
        logger.info("👷 Ожидание подключения рабочих узлов...")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Выключение...")
            self.running = False
    
    def _get_public_ip(self):
        """Получение публичного IP"""
        try:
            import urllib.request
            return urllib.request.urlopen('https://ifconfig.me').read().decode('utf-8')
        except:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except:
                return self.host
    
    def _run_worker_server(self):
        """Сервер для приема рабочих"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.worker_port))
        server.listen(10)
        
        logger.info(f"Сервер для рабочих запущен на {self.worker_port}")
        
        while self.running:
            try:
                conn, addr = server.accept()
                # Устанавливаем таймаут для сокета
                conn.settimeout(300)  # 5 минут
                
                worker_thread = threading.Thread(
                    target=self._handle_worker,
                    args=(conn, addr),
                    daemon=True
                )
                worker_thread.start()
            except Exception as e:
                if self.running:
                    logger.error(f"Ошибка сервера: {e}")
    
    def _handle_worker(self, conn, addr):
        """Обработка подключения рабочего - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        worker_id = f"{addr[0]}:{addr[1]}-{int(time.time())}"
        
        logger.info(f"📥 Подключился рабочий: {worker_id}")
        
        with self.lock:
            self.workers[worker_id] = {
                'conn': conn,
                'addr': addr,
                'last_seen': datetime.now(),
                'current_task': None,
                'status': 'ready',
                'capabilities': {}
            }
        
        try:
            # Устанавливаем большой таймаут
            conn.settimeout(300)
            
            # Сначала получаем регистрацию от рабочего
            try:
                data = conn.recv(4096)
                if data:
                    try:
                        message = json.loads(data.decode('utf-8'))
                        if message.get('type') == 'capabilities':
                            with self.lock:
                                if worker_id in self.workers:
                                    self.workers[worker_id]['capabilities'] = message.get('capabilities', {})
                                    self.workers[worker_id]['name'] = message.get('name', 'Unknown')
                                    logger.info(f"📋 Рабочий {worker_id} зарегистрирован как: {message.get('name', 'Unknown')}")
                    except json.JSONDecodeError:
                        logger.warning(f"Некорректный JSON от {worker_id}")
            except socket.timeout:
                logger.warning(f"Таймаут регистрации от {worker_id}")
            
            # Отправляем подтверждение регистрации
            welcome_msg = {
                'type': 'welcome',
                'worker_id': worker_id,
                'status': 'connected',
                'message': 'Добро пожаловать в AI Network!'
            }
            conn.sendall(json.dumps(welcome_msg).encode())
            
            # Основной цикл обработки рабочего
            while self.running:
                try:
                    # Получаем данные от рабочего
                    data = conn.recv(4096)
                    
                    if data:
                        try:
                            message = json.loads(data.decode('utf-8'))
                            
                            if message.get('type') == 'heartbeat':
                                with self.lock:
                                    if worker_id in self.workers:
                                        self.workers[worker_id]['last_seen'] = datetime.now()
                                
                                # Отправляем ответ
                                response = {'type': 'heartbeat_ack', 'timestamp': time.time()}
                                conn.sendall(json.dumps(response).encode())
                                
                            elif message.get('type') == 'result':
                                task_id = message.get('task_id')
                                result = message.get('result')
                                
                                with self.lock:
                                    if worker_id in self.workers:
                                        self.workers[worker_id]['current_task'] = None
                                        self.workers[worker_id]['status'] = 'ready'
                                    
                                    if task_id in self.tasks:
                                        if result.get('status') == 'success':
                                            self.tasks[task_id]['status'] = 'completed'
                                            self.tasks[task_id]['result'] = result
                                            logger.info(f"✅ Задача {task_id} успешно выполнена рабочим {worker_id}")
                                        else:
                                            self.tasks[task_id]['status'] = 'failed'
                                            self.tasks[task_id]['result'] = result
                                            logger.warning(f"❌ Задача {task_id} завершилась с ошибкой: {result.get('message')}")
                                
                                self._assign_tasks()
                            
                        except json.JSONDecodeError:
                            logger.warning(f"Некорректный JSON от {worker_id}")
                    
                    # Обновляем время последней активности
                    with self.lock:
                        if worker_id in self.workers:
                            self.workers[worker_id]['last_seen'] = datetime.now()
                    
                    time.sleep(1)  # Небольшая пауза чтобы не грузить CPU
                    
                except socket.timeout:
                    # Таймаут - это нормально, просто продолжаем
                    continue
                except ConnectionResetError:
                    logger.warning(f"Соединение с {worker_id} разорвано")
                    break
                except Exception as e:
                    logger.error(f"Ошибка обработки рабочего {worker_id}: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Рабочий {worker_id} отключился: {e}")
        finally:
            self._remove_worker(worker_id)
            try:
                conn.close()
            except:
                pass
    
    def _send_heartbeats(self):
        """Отправка heartbeat рабочим"""
        while self.running:
            try:
                time.sleep(30)  # Отправляем heartbeat каждые 30 секунд
                
                with self.lock:
                    workers_to_check = list(self.workers.keys())
                
                for worker_id in workers_to_check:
                    try:
                        with self.lock:
                            if worker_id not in self.workers:
                                continue
                            worker = self.workers[worker_id]
                        
                        # Проверяем, не было ли активности более 60 секунд
                        time_diff = (datetime.now() - worker['last_seen']).total_seconds()
                        if time_diff > 60:
                            logger.debug(f"Отправляем heartbeat рабочему {worker_id}")
                            try:
                                conn = worker['conn']
                                heartbeat_msg = {'type': 'heartbeat', 'timestamp': time.time()}
                                conn.sendall(json.dumps(heartbeat_msg).encode())
                            except:
                                # Если ошибка отправки, удаляем рабочего
                                self._remove_worker(worker_id)
                    
                    except Exception as e:
                        logger.debug(f"Ошибка heartbeat для {worker_id}: {e}")
                
            except Exception as e:
                logger.error(f"Ошибка потока heartbeat: {e}")
                time.sleep(30)
    
    def _task_processor(self):
        """Обработчик задач"""
        while self.running:
            try:
                self._assign_tasks()
                time.sleep(2)
            except Exception as e:
                logger.error(f"Ошибка обработчика задач: {e}")
                time.sleep(5)
    
    def _assign_tasks(self):
        """Назначение задач свободным рабочим"""
        with self.lock:
            if not self.task_queue:
                return
            
            # Ищем свободных рабочих
            free_workers = []
            for worker_id, worker in self.workers.items():
                if worker['status'] == 'ready' and not worker.get('current_task'):
                    free_workers.append(worker_id)
            
            if not free_workers:
                return
            
            # Назначаем задачи
            for worker_id in free_workers:
                if not self.task_queue:
                    break
                
                task_id = self.task_queue.pop(0)
                task = self.tasks[task_id]
                
                if task['status'] == 'pending':
                    if self._send_task_to_worker(worker_id, task_id, task):
                        task['status'] = 'running'
                        task['worker'] = worker_id
                        
                        self.workers[worker_id]['current_task'] = task_id
                        self.workers[worker_id]['status'] = 'busy'
                        
                        logger.info(f"📤 Задача {task_id} назначена рабочему {worker_id}")
    
    def _send_task_to_worker(self, worker_id, task_id, task):
        """Отправка задачи рабочему"""
        try:
            with self.lock:
                if worker_id not in self.workers:
                    return False
                
                conn = self.workers[worker_id]['conn']
            
            task_message = {
                'type': 'task',
                'task_id': task_id,
                'task_type': task['type'],
                'data': task['data']
            }
            
            conn.sendall(json.dumps(task_message).encode())
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки задачи рабочему {worker_id}: {e}")
            return False
    
    def _remove_worker(self, worker_id):
        """Удаление отключившегося рабочего"""
        with self.lock:
            if worker_id in self.workers:
                current_task = self.workers[worker_id].get('current_task')
                
                if current_task and current_task in self.tasks:
                    # Возвращаем задачу в очередь
                    self.tasks[current_task]['status'] = 'pending'
                    self.tasks[current_task]['worker'] = None
                    self.task_queue.insert(0, current_task)
                    logger.warning(f"🚨 Задача {current_task} возвращена в очередь из-за отключения рабочего {worker_id}")
                
                del self.workers[worker_id]
                logger.info(f"🗑️ Рабочий {worker_id} удален")
    
    def _cleanup_workers(self):
        """Очистка неактивных рабочих"""
        while self.running:
            try:
                time.sleep(120)  # Проверяем каждые 2 минуты
                
                with self.lock:
                    to_remove = []
                    now = datetime.now()
                    
                    for worker_id, worker in self.workers.items():
                        time_diff = (now - worker['last_seen']).total_seconds()
                        if time_diff > 300:  # 5 минут без активности
                            to_remove.append(worker_id)
                    
                    for worker_id in to_remove:
                        logger.warning(f"⏰ Рабочий {worker_id} удален по таймауту (неактивен {time_diff:.0f} сек)")
                        try:
                            self.workers[worker_id]['conn'].close()
                        except:
                            pass
                        self._remove_worker(worker_id)
                
            except Exception as e:
                logger.error(f"Ошибка очистки: {e}")

# ========== Клиент для рабочих узлов ==========
class WorkerClient:
    def __init__(self, host='localhost', port=8888, name=None):
        self.host = host
        self.port = port
        self.name = name or f"Worker_{os.getpid()}_{random.randint(1000, 9999)}"
        self.running = True
        self.connected = False
    
    def start(self):
        """Запуск рабочего клиента"""
        logger.info(f"👷 Запуск рабочего: {self.name}")
        logger.info(f"📡 Подключение к {self.host}:{self.port}")
        
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((self.host, self.port))
                
                # Устанавливаем большой таймаут после подключения
                sock.settimeout(300)
                
                # Отправляем информацию о себе
                capabilities = {
                    'type': 'capabilities',
                    'name': self.name,
                    'cpu_cores': os.cpu_count() or 1,
                    'supports': ['matrix_mult', 'calculation', 'nn_inference']
                }
                
                sock.sendall(json.dumps(capabilities).encode())
                
                # Ждем приветственное сообщение
                data = sock.recv(4096)
                if data:
                    welcome = json.loads(data.decode())
                    if welcome.get('type') == 'welcome':
                        logger.info(f"✅ {welcome.get('message')}")
                        logger.info(f"🆔 Ваш ID: {welcome.get('worker_id')}")
                
                self.connected = True
                logger.info(f"🚀 Рабочий {self.name} готов к работе!")
                
                # Запускаем поток для отправки heartbeat
                heartbeat_thread = threading.Thread(target=self._send_heartbeats, args=(sock,), daemon=True)
                heartbeat_thread.start()
                
                # Основной цикл
                while self.running and self.connected:
                    try:
                        # Получаем задачи
                        data = sock.recv(4096)
                        
                        if data:
                            try:
                                message = json.loads(data.decode('utf-8'))
                                
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
                                        'result': result
                                    }
                                    
                                    sock.sendall(json.dumps(response).encode())
                                    logger.info(f"✅ Задача {task_id} выполнена")
                                
                                elif message.get('type') == 'heartbeat':
                                    # Отвечаем на heartbeat от сервера
                                    response = {'type': 'heartbeat_ack', 'timestamp': time.time()}
                                    sock.sendall(json.dumps(response).encode())
                                    
                            except json.JSONDecodeError:
                                logger.warning("Некорректный JSON от сервера")
                        
                    except socket.timeout:
                        continue
                    except ConnectionResetError:
                        logger.error("🔌 Соединение разорвано сервером")
                        self.connected = False
                        break
                    except Exception as e:
                        logger.error(f"Ошибка обработки: {e}")
                        self.connected = False
                        break
                
                sock.close()
                self.connected = False
                logger.warning("🔌 Отключено от сервера")
                
            except ConnectionRefusedError:
                logger.warning("❌ Не могу подключиться к серверу, повтор через 10 секунд...")
                time.sleep(10)
            except socket.timeout:
                logger.warning("⏰ Таймаут подключения, повтор...")
                time.sleep(10)
            except Exception as e:
                logger.error(f"Ошибка подключения: {e}")
                time.sleep(10)
    
    def _send_heartbeats(self, sock):
        """Отправка heartbeat серверу"""
        while self.running and self.connected:
            try:
                time.sleep(20)  # Отправляем каждые 20 секунд
                
                heartbeat = {
                    'type': 'heartbeat',
                    'timestamp': time.time(),
                    'worker_name': self.name
                }
                
                sock.sendall(json.dumps(heartbeat).encode())
                
            except:
                break
    
    def _process_task(self, task_type, task_data):
        """Обработка задачи"""
        try:
            start_time = time.time()
            
            if task_type == 'matrix_mult':
                size = task_data.get('size', 10)
                
                a = MathUtils.random_matrix(size)
                b = MathUtils.random_matrix(size)
                
                result = MathUtils.matrix_multiply(a, b)
                
                execution_time = time.time() - start_time
                
                return {
                    'status': 'success',
                    'task_type': task_type,
                    'matrix_size': size,
                    'execution_time': round(execution_time, 3),
                    'worker': self.name,
                    'checksum': hashlib.md5(str(result).encode()).hexdigest()[:8] if hashlib else 'no_hash'
                }
            
            elif task_type == 'calculation':
                numbers = task_data.get('numbers', [random.random() for _ in range(10)])
                
                # Выполняем несколько операций
                sum_result = sum(numbers)
                avg_result = sum_result / len(numbers)
                
                execution_time = time.time() - start_time
                
                return {
                    'status': 'success',
                    'task_type': task_type,
                    'sum': round(sum_result, 3),
                    'average': round(avg_result, 3),
                    'count': len(numbers),
                    'execution_time': round(execution_time, 3),
                    'worker': self.name
                }
            
            elif task_type == 'nn_inference':
                input_size = task_data.get('input_size', 3)
                inputs = [random.random() for _ in range(input_size)]
                
                nn = SimpleNeuralNetwork(input_size=input_size)
                result = nn.predict(inputs)
                
                execution_time = time.time() - start_time
                
                return {
                    'status': 'success',
                    'task_type': task_type,
                    'input_size': input_size,
                    'output': [round(x, 4) for x in result],
                    'execution_time': round(execution_time, 3),
                    'worker': self.name
                }
            
            else:
                return {
                    'status': 'error',
                    'message': f'Неизвестный тип задачи: {task_type}',
                    'worker': self.name
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'worker': self.name
            }

# ========== Главная функция ==========
def main():
    parser = argparse.ArgumentParser(description="🚀 Децентрализованная AI сеть для VPS")
    
    parser.add_argument('--coordinator', action='store_true', help='Запустить координатор на VPS')
    parser.add_argument('--worker', action='store_true', help='Запустить рабочий узел')
    parser.add_argument('--name', help='Имя рабочего узла')
    parser.add_argument('--host', default='0.0.0.0', help='Хост сервера')
    parser.add_argument('--port', type=int, default=8888, help='Порт сервера')
    parser.add_argument('--web-port', type=int, default=8890, help='Порт веб-интерфейса')
    
    args = parser.parse_args()
    
    if args.coordinator:
        print("=" * 60)
        print("🚀 ЗАПУСК AI NETWORK НА VPS")
        print("=" * 60)
        public_ip = CoordinatorVPS()._get_public_ip()
        print(f"🌐 Веб-интерфейс: http://{public_ip}:{args.web_port}")
        print(f"📡 Порт для рабочих: {args.port}")
        print("=" * 60)
        print("\n📢 Инструкция для подключения рабочих:")
        print(f"python3 ai_network.py --worker --host {public_ip} --port {args.port} --name 'Ваше_Имя'")
        print("=" * 60)
        
        coordinator = CoordinatorVPS(
            host=args.host,
            worker_port=args.port,
            web_port=args.web_port
        )
        
        # Запускаем Flask в отдельном потоке
        import warnings
        warnings.filterwarnings("ignore", message=".*Werkzeug.*")
        
        flask_thread = threading.Thread(
            target=lambda: coordinator.app.run(
                host=args.host,
                port=args.web_port,
                debug=False,
                use_reloader=False
            ),
            daemon=True
        )
        flask_thread.start()
        
        coordinator.start()
    
    elif args.worker:
        worker = WorkerClient(
            host=args.host,
            port=args.port,
            name=args.name
        )
        worker.start()
    
    else:
        print("""
        🚀 AI NETWORK MVP ДЛЯ VPS
        
        Команды:
        --coordinator    Запустить сервер на VPS
        --worker         Подключиться как рабочий узел
        
        Примеры:
        
        1. На VPS (сервер):
        python3 ai_network.py --coordinator --host 0.0.0.0 --port 8888
        
        2. На клиенте (рабочий узел):
        python3 ai_network.py --worker --host IP_VPS --port 8888 --name "My_PC"
        
        🔧 Требования:
        - Python 3.7+
        - Открытые порты на VPS: 8888 и 8890
        """)

if __name__ == "__main__":
    # Добавим hashlib если не импортирован
    try:
        import hashlib
    except:
        hashlib = None
    
    main()
