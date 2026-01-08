#!/usr/bin/env python3
"""
🚀 AI Network - Упрощенная рабочая версия
Все через один порт 8888, без Flask, без HTTP
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
import sys
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("AI-Network")

# ========== ДАТА-КЛАССЫ ==========
class TaskType(Enum):
    MATRIX_MULT = "matrix_mult"
    CALCULATION = "calculation"
    NN_INFERENCE = "nn_inference"

@dataclass
class Task:
    id: str
    type: TaskType
    data: Dict
    status: str = "pending"  # pending, running, completed, failed
    created: float = None
    worker_id: str = None
    result: Dict = None
    started: float = None
    completed: float = None
    
    def __post_init__(self):
        if self.created is None:
            self.created = time.time()

@dataclass  
class Worker:
    id: str
    name: str
    addr: tuple
    conn: socket.socket
    status: str = "connected"
    last_seen: float = None
    current_task: str = None
    capabilities: Dict = None
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = time.time()
        if self.capabilities is None:
            self.capabilities = {}

# ========== КООРДИНАТОР ==========
class NetworkCoordinator:
    """Упрощенный координатор - все через сокеты на одном порту"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8888):
        self.host = host
        self.port = port
        self.public_ip = "185.185.142.113"
        
        # Хранилища
        self.workers: Dict[str, Worker] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[str] = []  # Очередь task_id
        
        # Синхронизация
        self.lock = threading.RLock()
        self.running = False
        
        # Статистика
        self.stats = {
            "start_time": time.time(),
            "tasks_processed": 0,
            "workers_connected": 0
        }
        
        logger.info(f"Координатор инициализирован на {host}:{port}")
    
    def _create_socket(self) -> socket.socket:
        """Создать и настроить сокет"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1)  # Таймаут для accept
        return sock
    
    def _send_json(self, conn: socket.socket, data: Dict):
        """Отправить JSON через сокет"""
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            conn.sendall(json_str.encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки JSON: {e}")
            return False
    
    def _receive_json(self, conn: socket.socket, timeout: int = 5) -> Optional[Dict]:
        """Получить JSON из сокета"""
        try:
            conn.settimeout(timeout)
            buffer = b""
            
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                
                # Пробуем распарсить JSON
                try:
                    data = json.loads(buffer.decode('utf-8', errors='ignore'))
                    return data
                except json.JSONDecodeError:
                    # Неполный JSON, продолжаем чтение
                    continue
                    
        except socket.timeout:
            logger.debug("Таймаут приема данных")
        except Exception as e:
            logger.error(f"Ошибка приема JSON: {e}")
        
        return None
    
    def _create_task(self, task_type: str, task_data: Dict) -> str:
        """Создать новую задачу"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        with self.lock:
            task = Task(
                id=task_id,
                type=TaskType(task_type),
                data=task_data,
                created=time.time()
            )
            self.tasks[task_id] = task
            self.task_queue.append(task_id)
            
            self.stats["tasks_processed"] += 1
        
        logger.info(f"Создана задача {task_id}: {task_type}")
        return task_id
    
    def _assign_task_to_worker(self, worker_id: str, task_id: str) -> bool:
        """Назначить задачу рабочему"""
        with self.lock:
            if worker_id not in self.workers:
                return False
            
            if task_id not in self.tasks:
                return False
            
            worker = self.workers[worker_id]
            task = self.tasks[task_id]
            
            # Если рабочий уже занят
            if worker.current_task:
                return False
            
            # Если задача уже выполняется
            if task.status != "pending":
                return False
            
            # Отправляем задачу рабочему
            task_message = {
                "type": "task",
                "task_id": task_id,
                "task_type": task.type.value,
                "data": task.data,
                "timestamp": time.time()
            }
            
            if self._send_json(worker.conn, task_message):
                task.status = "running"
                task.worker_id = worker_id
                task.started = time.time()
                worker.current_task = task_id
                
                # Удаляем из очереди
                if task_id in self.task_queue:
                    self.task_queue.remove(task_id)
                
                logger.info(f"Задача {task_id} назначена рабочему {worker_id}")
                return True
        
        return False
    
    def _process_worker_message(self, worker_id: str, conn: socket.socket, message: Dict):
        """Обработать сообщение от рабочего"""
        try:
            msg_type = message.get("type")
            
            if msg_type == "register":
                # Регистрация рабочего
                worker_name = message.get("name", f"Worker_{worker_id[:6]}")
                capabilities = message.get("capabilities", {})
                
                with self.lock:
                    if worker_id in self.workers:
                        worker = self.workers[worker_id]
                        worker.name = worker_name
                        worker.capabilities = capabilities
                        worker.last_seen = time.time()
                        
                        logger.info(f"Рабочий зарегистрирован: {worker_name}")
                        
                        # Отправляем подтверждение
                        response = {
                            "type": "welcome",
                            "worker_id": worker_id,
                            "message": f"Добро пожаловать, {worker_name}!",
                            "timestamp": time.time(),
                            "coordinator": self.public_ip
                        }
                        self._send_json(conn, response)
            
            elif msg_type == "heartbeat":
                # Обновляем время последней активности
                with self.lock:
                    if worker_id in self.workers:
                        self.workers[worker_id].last_seen = time.time()
                
                # Отправляем подтверждение
                response = {"type": "heartbeat_ack", "timestamp": time.time()}
                self._send_json(conn, response)
            
            elif msg_type == "task_result":
                # Результат выполнения задачи
                task_id = message.get("task_id")
                result = message.get("result", {})
                
                with self.lock:
                    if worker_id in self.workers:
                        self.workers[worker_id].current_task = None
                        self.workers[worker_id].last_seen = time.time()
                    
                    if task_id in self.tasks:
                        task = self.tasks[task_id]
                        
                        if result.get("status") == "success":
                            task.status = "completed"
                            task.result = result
                            task.completed = time.time()
                            logger.info(f"Задача {task_id} успешно выполнена")
                        else:
                            task.status = "failed"
                            task.result = result
                            logger.warning(f"Задача {task_id} провалена")
                
                # Пытаемся назначить следующую задачу
                self._assign_pending_tasks()
            
            elif msg_type == "submit_task":
                # Рабочий может также отправлять задачи (как клиент)
                task_type = message.get("task_type")
                task_data = message.get("data", {})
                
                if task_type:
                    task_id = self._create_task(task_type, task_data)
                    
                    response = {
                        "type": "task_submitted",
                        "task_id": task_id,
                        "status": "success",
                        "timestamp": time.time()
                    }
                    self._send_json(conn, response)
                    
                    # Пытаемся сразу назначить
                    self._assign_pending_tasks()
            
            elif msg_type == "get_stats":
                # Запрос статистики
                stats = self._get_stats()
                response = {
                    "type": "stats",
                    "stats": stats,
                    "timestamp": time.time()
                }
                self._send_json(conn, response)
            
            elif msg_type == "get_tasks":
                # Запрос списка задач
                tasks_list = []
                with self.lock:
                    for task_id, task in self.tasks.items():
                        tasks_list.append({
                            "id": task.id,
                            "type": task.type.value,
                            "status": task.status,
                            "created": task.created,
                            "worker_id": task.worker_id
                        })
                
                response = {
                    "type": "tasks_list",
                    "tasks": tasks_list,
                    "timestamp": time.time()
                }
                self._send_json(conn, response)
            
            else:
                logger.warning(f"Неизвестный тип сообщения от рабочего {worker_id}: {msg_type}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения от {worker_id}: {e}")
    
    def _assign_pending_tasks(self):
        """Назначить все pending задачи свободным рабочим"""
        with self.lock:
            # Ищем свободных рабочих
            free_workers = []
            for worker_id, worker in self.workers.items():
                if worker.status == "connected" and not worker.current_task:
                    free_workers.append(worker_id)
            
            if not free_workers:
                return
            
            # Ищем pending задачи
            pending_tasks = []
            for task_id in self.task_queue[:]:  # Копируем список
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    if task.status == "pending":
                        pending_tasks.append(task_id)
            
            if not pending_tasks:
                return
            
            # Назначаем задачи
            for worker_id in free_workers:
                if not pending_tasks:
                    break
                
                task_id = pending_tasks.pop(0)
                self._assign_task_to_worker(worker_id, task_id)
    
    def _cleanup_inactive_workers(self):
        """Очистка неактивных рабочих"""
        while self.running:
            try:
                time.sleep(30)  # Проверяем каждые 30 секунд
                
                current_time = time.time()
                to_remove = []
                
                with self.lock:
                    for worker_id, worker in self.workers.items():
                        # Если рабочий неактивен более 2 минут
                        if current_time - worker.last_seen > 120:
                            to_remove.append(worker_id)
                
                for worker_id in to_remove:
                    logger.warning(f"Рабочий {worker_id} удален по таймауту")
                    
                    with self.lock:
                        if worker_id in self.workers:
                            worker = self.workers[worker_id]
                            
                            # Если у рабочего была задача, возвращаем ее в очередь
                            if worker.current_task:
                                task_id = worker.current_task
                                if task_id in self.tasks:
                                    task = self.tasks[task_id]
                                    if task.status == "running":
                                        task.status = "pending"
                                        task.worker_id = None
                                        self.task_queue.insert(0, task_id)
                                        logger.info(f"Задача {task_id} возвращена в очередь")
                            
                            # Закрываем соединение
                            try:
                                worker.conn.close()
                            except:
                                pass
                            
                            del self.workers[worker_id]
                
            except Exception as e:
                logger.error(f"Ошибка очистки рабочих: {e}")
    
    def _get_stats(self) -> Dict:
        """Получить статистику"""
        with self.lock:
            workers_count = len([w for w in self.workers.values() if w.status == "connected"])
            tasks_total = len(self.tasks)
            tasks_pending = len([t for t in self.tasks.values() if t.status == "pending"])
            tasks_running = len([t for t in self.tasks.values() if t.status == "running"])
            tasks_completed = len([t for t in self.tasks.values() if t.status == "completed"])
            tasks_failed = len([t for t in self.tasks.values() if t.status == "failed"])
            
            return {
                "workers_connected": workers_count,
                "tasks_total": tasks_total,
                "tasks_pending": tasks_pending,
                "tasks_running": tasks_running,
                "tasks_completed": tasks_completed,
                "tasks_failed": tasks_failed,
                "queue_length": len(self.task_queue),
                "uptime": time.time() - self.stats["start_time"],
                "timestamp": time.time(),
                "coordinator": self.public_ip,
                "port": self.port
            }
    
    def _handle_worker_connection(self, conn: socket.socket, addr: tuple):
        """Обработка подключения рабочего/клиента"""
        worker_id = f"worker_{addr[0]}:{addr[1]}_{int(time.time())}"
        
        logger.info(f"Новое подключение от {addr[0]}:{addr[1]}")
        
        try:
            # Создаем объект рабочего
            worker = Worker(
                id=worker_id,
                name=f"Worker_{worker_id[-6:]}",
                addr=addr,
                conn=conn,
                last_seen=time.time()
            )
            
            with self.lock:
                self.workers[worker_id] = worker
            
            # Отправляем приветственное сообщение
            welcome_msg = {
                "type": "connected",
                "worker_id": worker_id,
                "message": "Подключено к AI Network. Отправьте 'register' для начала работы.",
                "timestamp": time.time(),
                "coordinator": self.public_ip
            }
            self._send_json(conn, welcome_msg)
            
            # Основной цикл обработки сообщений
            while self.running:
                try:
                    # Читаем сообщение
                    message = self._receive_json(conn, timeout=30)
                    
                    if not message:
                        # Проверяем, не разорвано ли соединение
                        try:
                            # Пробуем отправить ping
                            ping_msg = {"type": "ping", "timestamp": time.time()}
                            if not self._send_json(conn, ping_msg):
                                raise ConnectionError("Соединение разорвано")
                        except:
                            logger.info(f"Соединение с {worker_id} разорвано")
                            break
                        
                        continue
                    
                    # Обрабатываем сообщение
                    self._process_worker_message(worker_id, conn, message)
                    
                except socket.timeout:
                    # Отправляем heartbeat запрос
                    heartbeat_msg = {"type": "heartbeat_req", "timestamp": time.time()}
                    self._send_json(conn, heartbeat_msg)
                    continue
                    
                except ConnectionError:
                    logger.info(f"Соединение с {worker_id} потеряно")
                    break
                    
                except Exception as e:
                    logger.error(f"Ошибка обработки сообщения от {worker_id}: {e}")
                    break
            
        except Exception as e:
            logger.error(f"Ошибка обработки подключения {addr}: {e}")
        finally:
            # Удаляем рабочего
            with self.lock:
                if worker_id in self.workers:
                    # Возвращаем задачу в очередь если есть
                    worker = self.workers[worker_id]
                    if worker.current_task:
                        task_id = worker.current_task
                        if task_id in self.tasks:
                            task = self.tasks[task_id]
                            if task.status == "running":
                                task.status = "pending"
                                task.worker_id = None
                                self.task_queue.insert(0, task_id)
                                logger.info(f"Задача {task_id} возвращена в очередь")
                    
                    del self.workers[worker_id]
            
            try:
                conn.close()
            except:
                pass
            
            logger.info(f"Подключение {worker_id} закрыто")
    
    def _run_server(self):
        """Запуск сервера"""
        try:
            self.server_socket = self._create_socket()
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            
            logger.info(f"Сервер запущен на {self.host}:{self.port}")
            logger.info(f"Публичный адрес: {self.public_ip}:{self.port}")
            
            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
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
                        logger.error(f"Ошибка accept: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка запуска сервера: {e}")
            self.running = False
    
    def start(self):
        """Запуск координатора"""
        self.running = True
        
        print("=" * 60)
        print("🚀 AI NETWORK COORDINATOR")
        print("=" * 60)
        print(f"🌐 Сервер: {self.public_ip}:{self.port}")
        print(f"📡 Порт: {self.port}")
        print(f"🏠 Локально: {self.host}:{self.port}")
        print("=" * 60)
        print("✅ Система запущена!")
        print("👷 Ожидание подключения рабочих...")
        print("📨 Клиенты могут подключаться через тот же порт")
        print("=" * 60)
        
        # Запускаем сервер
        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()
        
        # Запускаем очистку неактивных рабочих
        cleanup_thread = threading.Thread(target=self._cleanup_inactive_workers, daemon=True)
        cleanup_thread.start()
        
        # Запускаем обработчик задач
        task_thread = threading.Thread(target=self._task_processor_loop, daemon=True)
        task_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Остановка координатора...")
        finally:
            self.running = False
            if self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass
            print("👋 Координатор остановлен")
    
    def _task_processor_loop(self):
        """Цикл обработки задач"""
        while self.running:
            try:
                self._assign_pending_tasks()
                time.sleep(1)  # Проверяем каждую секунду
            except Exception as e:
                logger.error(f"Ошибка обработчика задач: {e}")
                time.sleep(5)

# ========== РАБОЧИЙ УЗЕЛ ==========
class WorkerNode:
    """Рабочий узел (может также отправлять задачи)"""
    
    def __init__(self, host: str, port: int = 8888, name: str = None):
        self.host = host
        self.port = port
        self.name = name or f"Worker_{random.randint(1000, 9999)}"
        self.worker_id = None
        self.running = False
        self.connected = False
    
    def _create_socket(self) -> socket.socket:
        """Создать клиентский сокет"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        return sock
    
    def _send_json(self, sock: socket.socket, data: Dict) -> bool:
        """Отправить JSON"""
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            sock.sendall(json_str.encode('utf-8'))
            return True
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            return False
    
    def _receive_json(self, sock: socket.socket, timeout: int = 5) -> Optional[Dict]:
        """Получить JSON"""
        try:
            sock.settimeout(timeout)
            buffer = b""
            
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                
                try:
                    return json.loads(buffer.decode('utf-8', errors='ignore'))
                except json.JSONDecodeError:
                    continue
                    
        except socket.timeout:
            return None
        except Exception as e:
            print(f"❌ Ошибка приема: {e}")
            return None
    
    def _process_task(self, task_type: str, task_data: Dict) -> Dict:
        """Обработать задачу"""
        start_time = time.time()
        
        try:
            if task_type == "matrix_mult":
                size = task_data.get("size", 10)
                
                # Генерируем матрицы
                matrix_a = [[random.random() for _ in range(size)] for _ in range(size)]
                matrix_b = [[random.random() for _ in range(size)] for _ in range(size)]
                
                # Умножаем
                result = [[0.0 for _ in range(size)] for _ in range(size)]
                for i in range(size):
                    for j in range(size):
                        for k in range(size):
                            result[i][j] += matrix_a[i][k] * matrix_b[k][j]
                
                exec_time = time.time() - start_time
                
                return {
                    "status": "success",
                    "task_type": task_type,
                    "matrix_size": size,
                    "execution_time": round(exec_time, 3),
                    "worker": self.name,
                    "checksum": hashlib.md5(str(result).encode()).hexdigest()[:8],
                    "timestamp": time.time()
                }
            
            elif task_type == "calculation":
                numbers = task_data.get("numbers", 1000)
                nums = [random.random() for _ in range(numbers)]
                
                exec_time = time.time() - start_time
                
                return {
                    "status": "success",
                    "task_type": task_type,
                    "results": {
                        "sum": sum(nums),
                        "average": sum(nums) / len(nums),
                        "min": min(nums),
                        "max": max(nums)
                    },
                    "numbers_count": len(nums),
                    "execution_time": round(exec_time, 3),
                    "worker": self.name,
                    "timestamp": time.time()
                }
            
            else:
                return {
                    "status": "error",
                    "message": f"Неизвестный тип задачи: {task_type}",
                    "timestamp": time.time()
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": time.time()
            }
    
    def _worker_loop(self, sock: socket.socket):
        """Основной цикл работы рабочего"""
        last_heartbeat = time.time()
        
        print(f"✅ Подключено к {self.host}:{self.port}")
        print("🔄 Ожидание задач...")
        
        try:
            while self.running and self.connected:
                current_time = time.time()
                
                # Отправляем heartbeat каждые 20 секунд
                if current_time - last_heartbeat > 20:
                    heartbeat = {"type": "heartbeat", "timestamp": current_time}
                    if self._send_json(sock, heartbeat):
                        last_heartbeat = current_time
                
                # Читаем сообщения
                message = self._receive_json(sock, timeout=2)
                
                if message:
                    msg_type = message.get("type")
                    
                    if msg_type == "task":
                        # Получили задачу
                        task_id = message.get("task_id")
                        task_type = message.get("task_type")
                        task_data = message.get("data", {})
                        
                        print(f"📥 Получена задача {task_id} ({task_type})")
                        
                        # Выполняем задачу
                        result = self._process_task(task_type, task_data)
                        
                        # Отправляем результат
                        response = {
                            "type": "task_result",
                            "task_id": task_id,
                            "result": result,
                            "timestamp": time.time()
                        }
                        
                        if self._send_json(sock, response):
                            if result.get("status") == "success":
                                print(f"✅ Задача {task_id} выполнена за {result.get('execution_time', 0):.3f} сек")
                            else:
                                print(f"⚠️ Задача {task_id} ошибка: {result.get('message')}")
                    
                    elif msg_type == "heartbeat_req":
                        # Ответ на heartbeat запрос
                        response = {"type": "heartbeat", "timestamp": time.time()}
                        self._send_json(sock, response)
                    
                    elif msg_type == "ping":
                        # Ответ на ping
                        response = {"type": "pong", "timestamp": time.time()}
                        self._send_json(sock, response)
                    
                    elif msg_type == "connected":
                        # Первое сообщение после подключения
                        print(f"📡 {message.get('message', 'Connected')}")
                        
                        # Регистрируемся как рабочий
                        register_msg = {
                            "type": "register",
                            "name": self.name,
                            "capabilities": {
                                "cpu_cores": 1,
                                "supported_tasks": ["matrix_mult", "calculation"],
                                "performance": random.randint(50, 100)
                            },
                            "timestamp": time.time()
                        }
                        self._send_json(sock, register_msg)
                    
                    elif msg_type == "welcome":
                        # Ответ на регистрацию
                        self.worker_id = message.get("worker_id")
                        print(f"👋 {message.get('message', 'Welcome')}")
                        print(f"🆔 ID: {self.worker_id}")
                
                elif message is None:
                    # Таймаут - это нормально, продолжаем цикл
                    continue
                    
        except Exception as e:
            print(f"❌ Ошибка в рабочем цикле: {e}")
            self.connected = False
        finally:
            try:
                sock.close()
            except:
                pass
    
    def start(self):
        """Запуск рабочего узла"""
        self.running = True
        
        print(f"👷 Запуск рабочего узла: {self.name}")
        print(f"📡 Подключение к {self.host}:{self.port}")
        print("=" * 50)
        
        reconnect_delay = 2
        max_reconnect_delay = 30
        
        while self.running:
            try:
                sock = self._create_socket()
                print(f"Подключение...")
                sock.connect((self.host, self.port))
                
                self.connected = True
                reconnect_delay = 2  # Сбрасываем задержку
                
                self._worker_loop(sock)
                
                if self.running and not self.connected:
                    print(f"🔌 Переподключение через {reconnect_delay} сек...")
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
                
            except ConnectionRefusedError:
                print(f"❌ Сервер недоступен. Повтор через {reconnect_delay} сек...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
                
            except socket.timeout:
                print(f"❌ Таймаут подключения. Повтор через {reconnect_delay} сек...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
                
            except KeyboardInterrupt:
                print("\n👋 Завершение работы...")
                self.running = False
                break
                
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
        
        print("👷 Рабочий узел остановлен")

# ========== КЛИЕНТ ДЛЯ ОТПРАВКИ ЗАДАЧ ==========
class TaskClient:
    """Простой клиент для отправки задач"""
    
    def __init__(self, host: str, port: int = 8888):
        self.host = host
        self.port = port
    
    def submit_task(self, task_type: str, task_data: Dict) -> Optional[str]:
        """Отправить задачу"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            print(f"Подключение к {self.host}:{self.port}...")
            sock.connect((self.host, self.port))
            
            # Сразу отправляем задачу (ведем себя как рабочий, но только отправляем)
            message = {
                "type": "submit_task",
                "task_type": task_type,
                "data": task_data,
                "timestamp": time.time()
            }
            
            json_str = json.dumps(message, ensure_ascii=False)
            sock.sendall(json_str.encode('utf-8'))
            
            # Ждем ответ
            sock.settimeout(5)
            buffer = b""
            
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                
                try:
                    response = json.loads(buffer.decode('utf-8', errors='ignore'))
                    sock.close()
                    
                    if response.get("type") == "task_submitted":
                        return response.get("task_id")
                    else:
                        print(f"❌ Ошибка: {response}")
                        return None
                        
                except json.JSONDecodeError:
                    continue
            
            sock.close()
            print("❌ Не получили ответ от сервера")
            return None
            
        except socket.timeout:
            print("❌ Таймаут подключения")
            return None
        except ConnectionRefusedError:
            print("❌ Сервер недоступен")
            return None
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None
    
    def get_stats(self) -> Optional[Dict]:
        """Получить статистику"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.host, self.port))
            
            message = {
                "type": "get_stats",
                "timestamp": time.time()
            }
            
            sock.sendall(json.dumps(message).encode('utf-8'))
            
            sock.settimeout(3)
            buffer = sock.recv(4096)
            sock.close()
            
            if buffer:
                return json.loads(buffer.decode('utf-8', errors='ignore'))
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
            return None
    
    def get_tasks(self) -> Optional[Dict]:
        """Получить список задач"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.host, self.port))
            
            message = {
                "type": "get_tasks",
                "timestamp": time.time()
            }
            
            sock.sendall(json.dumps(message).encode('utf-8'))
            
            sock.settimeout(3)
            buffer = sock.recv(4096)
            sock.close()
            
            if buffer:
                return json.loads(buffer.decode('utf-8', errors='ignore'))
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка получения списка задач: {e}")
            return None

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
                       help='Отправить задачу (тип: matrix_mult, calculation)')
    parser.add_argument('--stats', action='store_true',
                       help='Получить статистику сети')
    parser.add_argument('--tasks', action='store_true',
                       help='Получить список задач')
    parser.add_argument('--host', default="185.185.142.113",
                       help='Адрес координатора')
    parser.add_argument('--port', type=int, default=8888,
                       help='Порт координатора')
    parser.add_argument('--name', 
                       help='Имя рабочего узла')
    parser.add_argument('--size', type=int, default=10,
                       help='Размер матрицы (для matrix_mult)')
    parser.add_argument('--numbers', type=int, default=1000,
                       help='Количество чисел (для calculation)')
    
    args = parser.parse_args()
    
    if args.coordinator:
        coordinator = NetworkCoordinator(port=args.port)
        coordinator.start()
    
    elif args.worker:
        worker = WorkerNode(
            host=args.host,
            port=args.port,
            name=args.name
        )
        worker.start()
    
    elif args.submit:
        client = TaskClient(host=args.host, port=args.port)
        
        task_type = args.submit
        task_data = {}
        
        if task_type == "matrix_mult":
            task_data = {"size": args.size}
        elif task_type == "calculation":
            task_data = {"numbers": args.numbers}
        else:
            print(f"❌ Неизвестный тип задачи: {task_type}")
            return
        
        print(f"📨 Отправка задачи '{task_type}'...")
        task_id = client.submit_task(task_type, task_data)
        
        if task_id:
            print(f"✅ Задача отправлена: {task_id}")
            print(f"📊 Для проверки: python ai_network.py --tasks --host {args.host}")
        else:
            print("❌ Не удалось отправить задачу")
    
    elif args.stats:
        client = TaskClient(host=args.host, port=args.port)
        stats = client.get_stats()
        
        if stats and stats.get("type") == "stats":
            print("📊 СТАТИСТИКА СЕТИ:")
            print(f"   Рабочих онлайн: {stats['stats'].get('workers_connected', 0)}")
            print(f"   Всего задач: {stats['stats'].get('tasks_total', 0)}")
            print(f"   Ожидают: {stats['stats'].get('tasks_pending', 0)}")
            print(f"   Выполняются: {stats['stats'].get('tasks_running', 0)}")
            print(f"   Завершено: {stats['stats'].get('tasks_completed', 0)}")
            print(f"   Ошибок: {stats['stats'].get('tasks_failed', 0)}")
            print(f"   В очереди: {stats['stats'].get('queue_length', 0)}")
            print(f"   Аптайм: {stats['stats'].get('uptime', 0):.1f} сек")
            print(f"   Координатор: {stats['stats'].get('coordinator')}:{stats['stats'].get('port')}")
        else:
            print("❌ Не удалось получить статистику")
    
    elif args.tasks:
        client = TaskClient(host=args.host, port=args.port)
        tasks_data = client.get_tasks()
        
        if tasks_data and tasks_data.get("type") == "tasks_list":
            tasks = tasks_data.get("tasks", [])
            print(f"📝 ЗАДАЧИ ({len(tasks)}):")
            
            for task in tasks:
                status_icon = {
                    "pending": "⏳",
                    "running": "🔄",
                    "completed": "✅",
                    "failed": "❌"
                }.get(task.get("status", ""), "❓")
                
                print(f"  {status_icon} [{task.get('id', '?')[:8]}] {task.get('type', '?')} - {task.get('status', '?')}")
                if task.get("worker_id"):
                    print(f"     Рабочий: {task.get('worker_id', '?')[:8]}")
        else:
            print("❌ Не удалось получить список задач")
    
    else:
        print("=" * 70)
        print("🤖 AI NETWORK - ДЕЦЕНТРАЛИЗОВАННАЯ СЕТЬ ВЫЧИСЛЕНИЙ")
        print("=" * 70)
        print()
        print("КОМАНДЫ:")
        print("  --coordinator           Запустить координатор")
        print("  --worker                Запустить рабочий узел")
        print("  --submit [тип]          Отправить задачу")
        print("  --stats                 Получить статистику")
        print("  --tasks                 Получить список задач")
        print()
        print("ПРИМЕРЫ:")
        print("  1. Запуск координатора:")
        print("     python ai_network.py --coordinator --port 8888")
        print()
        print("  2. Подключение рабочего:")
        print("     python ai_network.py --worker --host 185.185.142.113 --name 'MyPC'")
        print()
        print("  3. Отправить задачу умножения матриц:")
        print("     python ai_network.py --submit matrix_mult --size 15")
        print()
        print("  4. Отправить вычислительную задачу:")
        print("     python ai_network.py --submit calculation --numbers 5000")
        print()
        print("  5. Получить статистику:")
        print("     python ai_network.py --stats --host 185.185.142.113")
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
