#!/usr/bin/env python3
"""
🚀 AI Network - Координатор без Flask, с сокетным клиентом
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
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("AI-Network")

# ========== МАТЕМАТИЧЕСКИЕ УТИЛИТЫ ==========
class MathUtils:
    @staticmethod
    def random_matrix(size: int) -> List[List[float]]:
        return [[random.random() for _ in range(size)] for _ in range(size)]
    
    @staticmethod
    def matrix_multiply(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        n = len(a)
        result = [[0.0 for _ in range(n)] for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                for k in range(n):
                    result[i][j] += a[i][k] * b[k][j]
        return result
    
    @staticmethod
    def sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

# ========== СЕТЕВЫЕ УТИЛИТЫ ==========
class NetworkUtils:
    @staticmethod
    def get_best_public_ip() -> str:
        try:
            hostname = socket.gethostname()
            addresses = []
            
            for info in socket.getaddrinfo(hostname, None):
                address = info[4][0]
                if address not in addresses:
                    addresses.append(address)
            
            ipv4_addresses = [ip for ip in addresses if ':' not in ip and not ip.startswith('127.')]
            if ipv4_addresses:
                public_ipv4 = [ip for ip in ipv4_addresses if not (
                    ip.startswith('10.') or 
                    ip.startswith('172.16.') or 
                    ip.startswith('192.168.')
                )]
                if public_ipv4:
                    return public_ipv4[0]
                return ipv4_addresses[0]
            
            return "0.0.0.0"
            
        except Exception as e:
            logger.error(f"Ошибка определения публичного IP: {e}")
            return "0.0.0.0"
    
    @staticmethod
    def create_socket() -> socket.socket:
        try:
            if socket.has_ipv6:
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                return sock
        except:
            pass
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock

# ========== КООРДИНАТОР СЕТИ ==========
class NetworkCoordinator:
    def __init__(self, host: str = None, worker_port: int = 8888, api_port: int = 8080):
        if host is None or host == "" or host == "0.0.0.0":
            self.public_host = NetworkUtils.get_best_public_ip()
            if self.public_host == "0.0.0.0":
                self.public_host = "185.185.142.113"
            self.host = "0.0.0.0"
        else:
            self.host = host
            self.public_host = host
        
        self.worker_port = worker_port
        self.api_port = api_port
        
        self.workers: Dict[str, Dict] = {}
        self.tasks: Dict[str, Dict] = {}
        self.task_queue: List[str] = []
        self.clients: Dict[str, Dict] = {}  # Для клиентов, которые только отправляют задачи
        
        self.lock = threading.RLock()
        self.running = False
        
        logger.info(f"Инициализация координатора")
        logger.info(f"Публичный адрес: {self.public_host}")
        logger.info(f"Порт для рабочих/клиентов: {self.worker_port}")
    
    def _get_stats(self) -> Dict[str, Any]:
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
            'clients_count': len(self.clients),
            'timestamp': time.time(),
            'coordinator_uptime': time.time() - self.start_time,
            'public_host': self.public_host,
            'worker_port': self.worker_port
        }
    
    def _create_task(self, task_type: str, task_data: Dict) -> str:
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
        self._assign_tasks()
        return task_id
    
    def _assign_tasks(self):
        with self.lock:
            if not self.task_queue:
                return
            
            free_workers = []
            for worker_id, worker in self.workers.items():
                if worker.get('status') == 'connected' and not worker.get('current_task'):
                    free_workers.append(worker_id)
            
            if not free_workers:
                return
            
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
    
    def _handle_client_connection(self, conn: socket.socket, addr: tuple):
        """Обработка подключения клиента (только отправка задач)"""
        client_id = f"client_{addr[0]}:{addr[1]}-{int(time.time())}"
        
        logger.info(f"Новое подключение клиента: {client_id}")
        
        with self.lock:
            self.clients[client_id] = {
                'conn': conn,
                'addr': addr,
                'last_seen': time.time(),
                'type': 'client'
            }
        
        try:
            conn.settimeout(30)
            
            # Отправляем приветствие клиенту
            welcome_msg = {
                'type': 'welcome_client',
                'client_id': client_id,
                'message': 'Добро пожаловать в AI Network Client!',
                'timestamp': time.time(),
                'coordinator': self.public_host,
                'port': self.worker_port,
                'instructions': 'Отправьте JSON: {"type": "submit", "task_type": "...", "data": {...}}'
            }
            conn.sendall(json.dumps(welcome_msg).encode())
            
            # Основной цикл обработки клиента
            buffer = ""
            while self.running:
                try:
                    data = conn.recv(4096)
                    if not data:
                        logger.info(f"Клиент {client_id} отключился")
                        break
                    
                    buffer += data.decode('utf-8', errors='ignore')
                    messages = self._extract_json_messages(buffer)
                    
                    for message in messages:
                        self._process_client_message(client_id, conn, message)
                    
                    buffer = self._clean_buffer(buffer)
                    
                    with self.lock:
                        if client_id in self.clients:
                            self.clients[client_id]['last_seen'] = time.time()
                    
                except socket.timeout:
                    continue
                except ConnectionResetError:
                    logger.info(f"Соединение с клиентом {client_id} разорвано")
                    break
                except Exception as e:
                    logger.error(f"Ошибка обработки клиента {client_id}: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Ошибка соединения с клиентом {client_id}: {e}")
        finally:
            with self.lock:
                if client_id in self.clients:
                    del self.clients[client_id]
            try:
                conn.close()
            except:
                pass
    
    def _handle_worker_connection(self, conn: socket.socket, addr: tuple):
        """Обработка подключения рабочего (выполняет задачи)"""
        worker_id = f"worker_{addr[0]}:{addr[1]}-{int(time.time())}"
        
        logger.info(f"Новое подключение рабочего: {worker_id}")
        
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
            conn.settimeout(30)
            
            welcome_msg = {
                'type': 'welcome_worker',
                'worker_id': worker_id,
                'message': 'Добро пожаловать в AI Network!',
                'timestamp': time.time(),
                'coordinator': self.public_host
            }
            conn.sendall(json.dumps(welcome_msg).encode())
            
            buffer = ""
            while self.running:
                try:
                    data = conn.recv(4096)
                    if not data:
                        logger.info(f"Рабочий {worker_id} отключился")
                        break
                    
                    buffer += data.decode('utf-8', errors='ignore')
                    messages = self._extract_json_messages(buffer)
                    
                    for message in messages:
                        self._process_worker_message(worker_id, conn, message)
                    
                    buffer = self._clean_buffer(buffer)
                    
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
            self._remove_worker(worker_id)
            try:
                conn.close()
            except:
                pass
    
    def _process_client_message(self, client_id: str, conn: socket.socket, message: Dict):
        """Обработка сообщения от клиента"""
        try:
            msg_type = message.get('type')
            
            if msg_type == 'submit':
                # Клиент отправляет задачу
                task_type = message.get('task_type')
                task_data = message.get('data', {})
                
                if not task_type:
                    response = {
                        'type': 'error',
                        'message': 'Не указан task_type',
                        'timestamp': time.time()
                    }
                    conn.sendall(json.dumps(response).encode())
                    return
                
                # Создаем задачу
                task_id = self._create_task(task_type, task_data)
                
                # Отправляем подтверждение клиенту
                response = {
                    'type': 'submission_result',
                    'status': 'success',
                    'task_id': task_id,
                    'task_type': task_type,
                    'message': 'Задача успешно создана',
                    'timestamp': time.time()
                }
                conn.sendall(json.dumps(response).encode())
                
                logger.info(f"Клиент {client_id} отправил задачу {task_id} типа {task_type}")
            
            elif msg_type == 'get_status':
                # Клиент запрашивает статус задачи
                task_id = message.get('task_id')
                
                with self.lock:
                    task = self.tasks.get(task_id) if task_id else None
                
                response = {
                    'type': 'task_status',
                    'timestamp': time.time()
                }
                
                if task:
                    response.update({
                        'task_id': task_id,
                        'status': task.get('status'),
                        'worker': task.get('worker'),
                        'created': task.get('created'),
                        'result': task.get('result')
                    })
                else:
                    response.update({
                        'status': 'not_found',
                        'message': 'Задача не найдена'
                    })
                
                conn.sendall(json.dumps(response).encode())
            
            elif msg_type == 'get_stats':
                # Клиент запрашивает статистику
                stats = self._get_stats()
                response = {
                    'type': 'stats',
                    'stats': stats,
                    'timestamp': time.time()
                }
                conn.sendall(json.dumps(response).encode())
            
            elif msg_type == 'ping':
                # Пинг от клиента
                response = {
                    'type': 'pong',
                    'timestamp': time.time(),
                    'server_time': time.time()
                }
                conn.sendall(json.dumps(response).encode())
            
            else:
                response = {
                    'type': 'error',
                    'message': f'Неизвестный тип сообщения: {msg_type}',
                    'timestamp': time.time()
                }
                conn.sendall(json.dumps(response).encode())
                
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения от клиента {client_id}: {e}")
            try:
                error_response = {
                    'type': 'error',
                    'message': str(e),
                    'timestamp': time.time()
                }
                conn.sendall(json.dumps(error_response).encode())
            except:
                pass
    
    def _process_worker_message(self, worker_id: str, conn: socket.socket, message: Dict):
        """Обработка сообщения от рабочего"""
        try:
            msg_type = message.get('type')
            
            if msg_type == 'heartbeat':
                with self.lock:
                    if worker_id in self.workers:
                        self.workers[worker_id]['last_seen'] = time.time()
                
                ack = {'type': 'heartbeat_ack', 'timestamp': time.time()}
                conn.sendall(json.dumps(ack).encode())
                
            elif msg_type == 'capabilities':
                with self.lock:
                    if worker_id in self.workers:
                        self.workers[worker_id]['capabilities'] = message.get('capabilities', {})
                        self.workers[worker_id]['name'] = message.get('name', self.workers[worker_id]['name'])
                        logger.info(f"Обновлены данные рабочего {worker_id}: {self.workers[worker_id]['name']}")
                
            elif msg_type == 'result':
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
                
                self._assign_tasks()
                
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения от рабочего {worker_id}: {e}")
    
    def _remove_worker(self, worker_id: str):
        with self.lock:
            if worker_id in self.workers:
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
    
    def _extract_json_messages(self, buffer: str) -> List[Dict]:
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
                        try:
                            message = json.loads(buffer[start:i+1])
                            messages.append(message)
                        except:
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
        last_close = buffer.rfind('}')
        if last_close != -1:
            return buffer[last_close + 1:]
        return buffer
    
    def _run_server(self):
        """Запуск единого сервера для рабочих и клиентов"""
        try:
            server = NetworkUtils.create_socket()
            
            try:
                server.bind(("::", self.worker_port))
                logger.info(f"Сервер привязан к [::]:{self.worker_port} (IPv6)")
            except:
                server.bind(("0.0.0.0", self.worker_port))
                logger.info(f"Сервер привязан к 0.0.0.0:{self.worker_port} (IPv4)")
            
            server.listen(20)  # Увеличили очередь
            server.settimeout(1)
            
            logger.info(f"Сервер запущен. Подключение: {self.public_host}:{self.worker_port}")
            logger.info("Принимаем как рабочих (выполняют задачи), так и клиентов (отправляют задачи)")
            
            while self.running:
                try:
                    conn, addr = server.accept()
                    conn.settimeout(30)
                    
                    # Сначала определяем тип подключения
                    # В реальном приложении можно добавить handshake
                    # Сейчас просто создаем обработчик
                    
                    thread = threading.Thread(
                        target=self._handle_connection,
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
    
    def _handle_connection(self, conn: socket.socket, addr: tuple):
        """Определяет тип подключения и обрабатывает его"""
        try:
            # Устанавливаем короткий таймаут для handshake
            conn.settimeout(5)
            
            # Ждем первое сообщение от клиента/рабочего
            data = conn.recv(1024)
            
            if data:
                try:
                    message = json.loads(data.decode('utf-8', errors='ignore'))
                    conn_type = message.get('type', '')
                    
                    # Если это регистрация рабочего
                    if conn_type == 'register_worker':
                        self._handle_worker_connection(conn, addr)
                        return
                    
                    # Если это отправка задачи от клиента
                    elif conn_type == 'submit':
                        # Сначала обрабатываем это сообщение
                        conn.settimeout(30)
                        self._process_client_message(f"temp_{addr[0]}:{addr[1]}", conn, message)
                        # Затем продолжаем как клиент
                        conn.settimeout(30)
                        self._handle_client_connection(conn, addr)
                        return
                
                except json.JSONDecodeError:
                    pass
            
            # Если не определили тип, считаем это рабочим
            # (для обратной совместимости со старыми рабочими)
            conn.settimeout(30)
            self._handle_worker_connection(conn, addr)
            
        except socket.timeout:
            # Если таймаут, считаем это рабочим (старый рабочий не отправляет handshake)
            conn.settimeout(30)
            self._handle_worker_connection(conn, addr)
        except Exception as e:
            logger.error(f"Ошибка определения типа подключения: {e}")
            try:
                conn.close()
            except:
                pass
    
    def _cleanup_inactive(self):
        """Очистка неактивных рабочих и клиентов"""
        while self.running:
            try:
                time.sleep(60)
                
                current_time = time.time()
                to_remove_workers = []
                to_remove_clients = []
                
                with self.lock:
                    for worker_id, worker in self.workers.items():
                        last_seen = worker.get('last_seen', 0)
                        if current_time - last_seen > 120:
                            to_remove_workers.append(worker_id)
                    
                    for client_id, client in self.clients.items():
                        last_seen = client.get('last_seen', 0)
                        if current_time - last_seen > 120:
                            to_remove_clients.append(client_id)
                
                for worker_id in to_remove_workers:
                    logger.warning(f"Рабочий {worker_id} удален по таймауту")
                    try:
                        if worker_id in self.workers:
                            conn = self.workers[worker_id].get('conn')
                            if conn:
                                conn.close()
                    except:
                        pass
                    self._remove_worker(worker_id)
                
                for client_id in to_remove_clients:
                    logger.info(f"Клиент {client_id} удален по таймауту")
                    with self.lock:
                        if client_id in self.clients:
                            del self.clients[client_id]
                    
            except Exception as e:
                logger.error(f"Ошибка очистки: {e}")
    
    def _task_processor_loop(self):
        while self.running:
            try:
                self._assign_tasks()
                time.sleep(2)
            except Exception as e:
                logger.error(f"Ошибка обработчика задач: {e}")
                time.sleep(5)
    
    def start(self):
        self.running = True
        self.start_time = time.time()
        
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК AI NETWORK COORDINATOR")
        logger.info("=" * 60)
        logger.info(f"🌐 Сервер: {self.public_host}:{self.worker_port}")
        logger.info(f"📡 Принимаем: рабочие (8888) и клиенты (8888)")
        logger.info(f"🏠 Слушаем на: {self.host}:{self.worker_port}")
        logger.info("=" * 60)
        
        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()
        
        cleanup_thread = threading.Thread(target=self._cleanup_inactive, daemon=True)
        cleanup_thread.start()
        
        task_thread = threading.Thread(target=self._task_processor_loop, daemon=True)
        task_thread.start()
        
        try:
            logger.info("✅ Система запущена и готова к работе!")
            logger.info("👷 Ожидание подключения рабочих...")
            logger.info("📨 Ожидание подключения клиентов...")
            
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал завершения...")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
        finally:
            self.running = False
            logger.info("Координатор остановлен")

# ========== СОКЕТНЫЙ КЛИЕНТ ==========
class SocketClient:
    """Клиент для отправки задач через сокеты"""
    
    def __init__(self, host: str = "185.185.142.113", port: int = 8888):
        self.host = host
        self.port = port
        self.client_id = f"client_{random.randint(1000, 9999)}"
    
    def submit_task(self, task_type: str, task_data: Dict) -> Optional[str]:
        """Отправить задачу через сокет"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            print(f"Подключение к {self.host}:{self.port}...")
            sock.connect((self.host, self.port))
            
            # Сразу отправляем задачу
            message = {
                'type': 'submit',
                'task_type': task_type,
                'data': task_data,
                'timestamp': time.time(),
                'client_id': self.client_id
            }
            
            message_json = json.dumps(message)
            sock.sendall(message_json.encode())
            
            # Ждем ответ
            sock.settimeout(5)
            response_data = b""
            
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                
                # Пробуем распарсить JSON
                try:
                    response = json.loads(response_data.decode())
                    sock.close()
                    
                    if response.get('type') == 'submission_result' and response.get('status') == 'success':
                        return response.get('task_id')
                    else:
                        print(f"Ошибка: {response.get('message', 'Неизвестная ошибка')}")
                        return None
                        
                except json.JSONDecodeError:
                    # Неполный JSON, продолжаем чтение
                    continue
            
            sock.close()
            print("❌ Не получили ответ от сервера")
            return None
            
        except socket.timeout:
            print("❌ Таймаут подключения")
            return None
        except ConnectionRefusedError:
            print("❌ Сервер отказал в подключении")
            return None
        except Exception as e:
            print(f"❌ Ошибка: {type(e).__name__}: {e}")
            return None
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Получить статус задачи"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.host, self.port))
            
            message = {
                'type': 'get_status',
                'task_id': task_id,
                'timestamp': time.time(),
                'client_id': self.client_id
            }
            
            sock.sendall(json.dumps(message).encode())
            
            sock.settimeout(3)
            response_data = sock.recv(4096)
            sock.close()
            
            if response_data:
                return json.loads(response_data.decode())
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка получения статуса: {e}")
            return None
    
    def get_stats(self) -> Optional[Dict]:
        """Получить статистику сети"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.host, self.port))
            
            message = {
                'type': 'get_stats',
                'timestamp': time.time(),
                'client_id': self.client_id
            }
            
            sock.sendall(json.dumps(message).encode())
            
            sock.settimeout(3)
            response_data = sock.recv(4096)
            sock.close()
            
            if response_data:
                return json.loads(response_data.decode())
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
            return None

# ========== РАБОЧИЙ УЗЕЛ (упрощенный) ==========
class WorkerNode:
    """Рабочий узел для выполнения задач"""
    
    def __init__(self, server_host: str, server_port: int = 8888, name: str = None):
        self.server_host = server_host
        self.server_port = server_port
        self.name = name or f"Worker_{random.randint(1000, 9999)}"
        self.running = False
        self.worker_id = None
    
    def process_task(self, task_type: str, task_data: Dict) -> Dict:
        """Обработать задачу"""
        start_time = time.time()
        
        try:
            if task_type == 'matrix_mult':
                size = task_data.get('size', 10)
                matrix_a = [[random.random() for _ in range(size)] for _ in range(size)]
                matrix_b = [[random.random() for _ in range(size)] for _ in range(size)]
                
                # Умножение матриц
                result = [[0.0 for _ in range(size)] for _ in range(size)]
                for i in range(size):
                    for j in range(size):
                        for k in range(size):
                            result[i][j] += matrix_a[i][k] * matrix_b[k][j]
                
                execution_time = time.time() - start_time
                
                return {
                    'status': 'success',
                    'task_type': task_type,
                    'matrix_size': size,
                    'execution_time': round(execution_time, 3),
                    'worker': self.name,
                    'checksum': hashlib.md5(str(result).encode()).hexdigest()[:8]
                }
            
            elif task_type == 'calculation':
                numbers = task_data.get('numbers', 1000)
                random_numbers = [random.random() for _ in range(numbers)]
                
                results = {
                    'sum': sum(random_numbers),
                    'average': sum(random_numbers) / len(random_numbers),
                    'min': min(random_numbers),
                    'max': max(random_numbers)
                }
                
                execution_time = time.time() - start_time
                
                return {
                    'status': 'success',
                    'task_type': task_type,
                    'results': results,
                    'numbers_count': len(random_numbers),
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
    
    def start(self):
        """Запуск рабочего узла"""
        self.running = True
        
        print(f"👷 Запуск рабочего узла: {self.name}")
        print(f"📡 Подключение к серверу: {self.server_host}:{self.server_port}")
        print("=" * 50)
        
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                
                print(f"Подключение к {self.server_host}:{self.server_port}...")
                sock.connect((self.server_host, self.server_port))
                
                # Регистрация как рабочий
                registration = {
                    'type': 'register_worker',
                    'name': self.name,
                    'capabilities': {
                        'supported_tasks': ['matrix_mult', 'calculation']
                    }
                }
                
                sock.sendall(json.dumps(registration).encode())
                
                buffer = ""
                while self.running:
                    try:
                        data = sock.recv(4096)
                        if not data:
                            print("❌ Соединение разорвано")
                            break
                        
                        buffer += data.decode('utf-8', errors='ignore')
                        
                        # Ищем JSON сообщения
                        start = buffer.find('{')
                        while start != -1:
                            depth = 0
                            for i in range(start, len(buffer)):
                                if buffer[i] == '{':
                                    depth += 1
                                elif buffer[i] == '}':
                                    depth -= 1
                                    if depth == 0:
                                        try:
                                            message = json.loads(buffer[start:i+1])
                                            
                                            if message.get('type') == 'welcome_worker':
                                                self.worker_id = message.get('worker_id')
                                                print(f"✅ {message.get('message')}")
                                                print(f"🆔 Ваш ID: {self.worker_id}")
                                            
                                            elif message.get('type') == 'task':
                                                task_id = message.get('task_id')
                                                task_type = message.get('task_type')
                                                task_data = message.get('data', {})
                                                
                                                print(f"📥 Получена задача: {task_id} ({task_type})")
                                                
                                                # Обрабатываем задачу
                                                result = self.process_task(task_type, task_data)
                                                
                                                # Отправляем результат
                                                response = {
                                                    'type': 'result',
                                                    'task_id': task_id,
                                                    'result': result
                                                }
                                                
                                                sock.sendall(json.dumps(response).encode())
                                                
                                                if result['status'] == 'success':
                                                    print(f"✅ Задача {task_id} выполнена за {result.get('execution_time', 0):.3f} сек")
                                                else:
                                                    print(f"⚠️ Задача {task_id} завершилась с ошибкой")
                                            
                                            buffer = buffer[i+1:]
                                            start = buffer.find('{')
                                            break
                                            
                                        except json.JSONDecodeError:
                                            # Невалидный JSON, ищем дальше
                                            start = buffer.find('{', start + 1)
                                            break
                            
                            if depth != 0:
                                # Неполный JSON, выходим из цикла
                                break
                        
                    except socket.timeout:
                        # Отправляем heartbeat
                        heartbeat = {'type': 'heartbeat', 'worker_id': self.worker_id}
                        sock.sendall(json.dumps(heartbeat).encode())
                        continue
                    except Exception as e:
                        print(f"❌ Ошибка: {e}")
                        break
                
                sock.close()
                print("🔌 Переподключение через 5 сек...")
                time.sleep(5)
                
            except KeyboardInterrupt:
                print("\n👋 Завершение работы...")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Ошибка подключения: {e}")
                time.sleep(5)
        
        print("👷 Рабочий узел остановлен")

# ========== ГЛАВНАЯ ФУНКЦИЯ ==========
def main():
    parser = argparse.ArgumentParser(
        description="🚀 AI Network - Децентрализованная сеть вычислений",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--coordinator', action='store_true',
                       help='Запустить координатор сети')
    parser.add_argument('--worker', action='store_true',
                       help='Запустить рабочий узел')
    parser.add_argument('--submit', nargs='?', const='matrix_mult',
                       help='Отправить задачу через сокет (тип: matrix_mult, calculation)')
    parser.add_argument('--status', 
                       help='Проверить статус задачи (task_id)')
    parser.add_argument('--stats', action='store_true',
                       help='Получить статистику сети')
    parser.add_argument('--host', default="185.185.142.113",
                       help='Адрес координатора')
    parser.add_argument('--port', type=int, default=8888,
                       help='Порт координатора')
    parser.add_argument('--name', 
                       help='Имя рабочего узла')
    
    args = parser.parse_args()
    
    if args.coordinator:
        coordinator = NetworkCoordinator(
            host="0.0.0.0",
            worker_port=args.port
        )
        coordinator.start()
    
    elif args.worker:
        worker = WorkerNode(
            server_host=args.host,
            server_port=args.port,
            name=args.name
        )
        worker.start()
    
    elif args.submit:
        # Отправка задачи через сокетный клиент
        client = SocketClient(host=args.host, port=args.port)
        
        task_type = args.submit
        task_data = {}
        
        if task_type == 'matrix_mult':
            task_data = {'size': 10}
        elif task_type == 'calculation':
            task_data = {'numbers': 1000}
        
        print(f"📨 Отправка задачи типа '{task_type}'...")
        task_id = client.submit_task(task_type, task_data)
        
        if task_id:
            print(f"✅ Задача отправлена: {task_id}")
            print(f"📊 Статус: python ai_network.py --status {task_id} --host {args.host}")
        else:
            print("❌ Не удалось отправить задачу")
    
    elif args.status:
        # Проверка статуса задачи
        client = SocketClient(host=args.host, port=args.port)
        status = client.get_task_status(args.status)
        
        if status:
            print(f"📊 Статус задачи {args.status}:")
            print(json.dumps(status, indent=2, ensure_ascii=False))
        else:
            print(f"❌ Не удалось получить статус задачи {args.status}")
    
    elif args.stats:
        # Получение статистики
        client = SocketClient(host=args.host, port=args.port)
        stats = client.get_stats()
        
        if stats:
            print("📊 Статистика сети:")
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        else:
            print("❌ Не удалось получить статистику")
    
    else:
        print("=" * 70)
        print("🤖 AI NETWORK - ДЕЦЕНТРАЛИЗОВАННАЯ СЕТЬ ВЫЧИСЛЕНИЙ")
        print("=" * 70)
        print()
        print("КОМАНДЫ:")
        print("  --coordinator           Запустить координатор сети")
        print("  --worker                Запустить рабочий узел")
        print("  --submit [тип]          Отправить задачу")
        print("  --status <task_id>      Проверить статус задачи")
        print("  --stats                 Получить статистику сети")
        print()
        print("ПРИМЕРЫ:")
        print("  1. Запуск координатора:")
        print("     python ai_network.py --coordinator --port 8888")
        print()
        print("  2. Подключение рабочего:")
        print("     python ai_network.py --worker --host 185.185.142.113 --name 'MyPC'")
        print()
        print("  3. Отправить задачу:")
        print("     python ai_network.py --submit matrix_mult")
        print("     python ai_network.py --submit calculation")
        print()
        print("  4. Проверить статус:")
        print("     python ai_network.py --status abc123 --host 185.185.142.113")
        print()
        print("📡 Сервер: 185.185.142.113:8888")
        print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Программа завершена")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
