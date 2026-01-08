#!/usr/bin/env python3
"""
🚀 AI Network - Ультраупрощенная рабочая версия
Один порт 8888, чистые сокеты, без лишней сложности
"""

import socket
import threading
import json
import time
import random
import math
import hashlib
import argparse
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import uuid

# ========== КОНСТАНТЫ ==========
VPS_IP = "185.185.142.113"
PORT = 8888

# ========== ДАТА-КЛАССЫ ==========
@dataclass
class Task:
    id: str
    type: str  # "matrix_mult", "calculation"
    data: Dict
    status: str = "pending"  # pending, running, completed, failed
    created: float = None
    worker_id: str = None
    result: Dict = None
    
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
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = time.time()

# ========== КООРДИНАТОР ==========
class SimpleCoordinator:
    """Самый простой координатор - только самое необходимое"""
    
    def __init__(self, port: int = PORT):
        self.port = port
        self.workers: Dict[str, Worker] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[str] = []
        self.lock = threading.RLock()
        self.running = False
        self.server_socket = None
        
        print(f"🚀 Координатор на порту {port}")
    
    def _send_json(self, conn: socket.socket, data: Dict) -> bool:
        """Отправить JSON через сокет"""
        try:
            json_str = json.dumps(data)
            conn.sendall(json_str.encode())
            return True
        except:
            return False
    
    def _receive_json(self, conn: socket.socket) -> Optional[Dict]:
        """Получить JSON из сокета (упрощенно)"""
        try:
            conn.settimeout(2)
            data = conn.recv(4096)
            if data:
                return json.loads(data.decode())
        except:
            pass
        return None
    
    def _handle_connection(self, conn: socket.socket, addr: tuple):
        """Обработка подключения"""
        worker_id = f"worker_{addr[0]}_{addr[1]}_{int(time.time())}"
        
        print(f"📡 Подключение от {addr[0]}:{addr[1]}")
        
        try:
            # Создаем рабочего
            worker = Worker(
                id=worker_id,
                name=f"Worker_{worker_id[-6:]}",
                addr=addr,
                conn=conn,
                last_seen=time.time()
            )
            
            with self.lock:
                self.workers[worker_id] = worker
            
            # Отправляем приветствие
            self._send_json(conn, {
                "type": "welcome",
                "worker_id": worker_id,
                "message": "Connected to AI Network",
                "timestamp": time.time()
            })
            
            # Основной цикл
            while self.running:
                try:
                    # Получаем сообщение
                    message = self._receive_json(conn)
                    
                    if not message:
                        # Проверяем соединение
                        try:
                            conn.send(b"ping")
                            continue
                        except:
                            break
                    
                    msg_type = message.get("type")
                    
                    if msg_type == "register":
                        # Регистрация рабочего
                        worker_name = message.get("name", f"Worker_{worker_id[-6:]}")
                        with self.lock:
                            if worker_id in self.workers:
                                self.workers[worker_id].name = worker_name
                                self.workers[worker_id].last_seen = time.time()
                        
                        print(f"✅ Зарегистрирован: {worker_name}")
                        
                        self._send_json(conn, {
                            "type": "registered",
                            "worker_id": worker_id,
                            "name": worker_name,
                            "timestamp": time.time()
                        })
                    
                    elif msg_type == "heartbeat":
                        # Heartbeat
                        with self.lock:
                            if worker_id in self.workers:
                                self.workers[worker_id].last_seen = time.time()
                        
                        self._send_json(conn, {
                            "type": "heartbeat_ack",
                            "timestamp": time.time()
                        })
                    
                    elif msg_type == "submit_task":
                        # Клиент отправляет задачу
                        task_type = message.get("task_type")
                        task_data = message.get("data", {})
                        
                        if task_type:
                            # Создаем задачу
                            task_id = f"task_{uuid.uuid4().hex[:8]}"
                            
                            with self.lock:
                                task = Task(
                                    id=task_id,
                                    type=task_type,
                                    data=task_data,
                                    created=time.time()
                                )
                                self.tasks[task_id] = task
                                self.task_queue.append(task_id)
                            
                            print(f"📨 Создана задача {task_id}: {task_type}")
                            
                            # Отправляем подтверждение
                            self._send_json(conn, {
                                "type": "task_created",
                                "task_id": task_id,
                                "status": "created",
                                "timestamp": time.time()
                            })
                            
                            # Пытаемся назначить задачу
                            self._assign_tasks()
                    
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
                                    print(f"✅ Задача {task_id} выполнена")
                                else:
                                    task.status = "failed"
                                    task.result = result
                                    print(f"❌ Задача {task_id} провалена")
                        
                        # Пытаемся назначить следующую задачу
                        self._assign_tasks()
                    
                    elif msg_type == "get_stats":
                        # Запрос статистики
                        stats = self._get_stats()
                        self._send_json(conn, {
                            "type": "stats",
                            "stats": stats,
                            "timestamp": time.time()
                        })
                    
                    elif msg_type == "get_tasks":
                        # Запрос списка задач
                        tasks_list = []
                        with self.lock:
                            for task_id, task in self.tasks.items():
                                tasks_list.append({
                                    "id": task.id,
                                    "type": task.type,
                                    "status": task.status,
                                    "created": task.created,
                                    "worker_id": task.worker_id
                                })
                        
                        self._send_json(conn, {
                            "type": "tasks_list",
                            "tasks": tasks_list,
                            "timestamp": time.time()
                        })
                    
                    else:
                        # Неизвестный тип сообщения
                        print(f"⚠️ Неизвестный тип: {msg_type}")
                        
                except Exception as e:
                    print(f"❌ Ошибка обработки: {e}")
                    break
            
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
        finally:
            # Очищаем
            with self.lock:
                if worker_id in self.workers:
                    # Возвращаем задачу если есть
                    worker = self.workers[worker_id]
                    if worker.current_task:
                        task_id = worker.current_task
                        if task_id in self.tasks:
                            task = self.tasks[task_id]
                            if task.status == "running":
                                task.status = "pending"
                                task.worker_id = None
                                self.task_queue.insert(0, task_id)
                                print(f"↩️ Задача {task_id} возвращена в очередь")
                    
                    del self.workers[worker_id]
            
            try:
                conn.close()
            except:
                pass
            
            print(f"🔌 Отключен: {worker_id}")
    
    def _assign_tasks(self):
        """Назначить задачи свободным рабочим"""
        with self.lock:
            if not self.task_queue:
                return
            
            # Ищем свободных рабочих
            free_workers = []
            for worker_id, worker in self.workers.items():
                if worker.status == "connected" and not worker.current_task:
                    free_workers.append(worker_id)
            
            if not free_workers:
                return
            
            # Берем задачи из очереди
            pending_tasks = []
            for task_id in self.task_queue[:]:  # Копируем
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    if task.status == "pending":
                        pending_tasks.append(task_id)
            
            if not pending_tasks:
                return
            
            # Назначаем
            for worker_id in free_workers:
                if not pending_tasks:
                    break
                
                task_id = pending_tasks.pop(0)
                worker = self.workers[worker_id]
                task = self.tasks[task_id]
                
                # Отправляем задачу
                task_msg = {
                    "type": "task",
                    "task_id": task_id,
                    "task_type": task.type,
                    "data": task.data,
                    "timestamp": time.time()
                }
                
                if self._send_json(worker.conn, task_msg):
                    task.status = "running"
                    task.worker_id = worker_id
                    worker.current_task = task_id
                    
                    # Удаляем из очереди
                    if task_id in self.task_queue:
                        self.task_queue.remove(task_id)
                    
                    print(f"🎯 Задача {task_id} → {worker.name}")
    
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
                "workers": workers_count,
                "tasks_total": tasks_total,
                "tasks_pending": tasks_pending,
                "tasks_running": tasks_running,
                "tasks_completed": tasks_completed,
                "tasks_failed": tasks_failed,
                "queue": len(self.task_queue),
                "timestamp": time.time()
            }
    
    def _cleanup_loop(self):
        """Очистка неактивных рабочих"""
        while self.running:
            time.sleep(30)
            
            current_time = time.time()
            to_remove = []
            
            with self.lock:
                for worker_id, worker in self.workers.items():
                    if current_time - worker.last_seen > 60:  # 1 минута
                        to_remove.append(worker_id)
            
            for worker_id in to_remove:
                print(f"⏰ Удален по таймауту: {worker_id}")
                with self.lock:
                    if worker_id in self.workers:
                        worker = self.workers[worker_id]
                        
                        # Возвращаем задачу
                        if worker.current_task:
                            task_id = worker.current_task
                            if task_id in self.tasks:
                                task = self.tasks[task_id]
                                if task.status == "running":
                                    task.status = "pending"
                                    task.worker_id = None
                                    self.task_queue.insert(0, task_id)
                                    print(f"↩️ Возвращена задача {task_id}")
                        
                        # Закрываем соединение
                        try:
                            worker.conn.close()
                        except:
                            pass
                        
                        del self.workers[worker_id]
    
    def _task_assigner_loop(self):
        """Цикл назначения задач"""
        while self.running:
            self._assign_tasks()
            time.sleep(1)
    
    def start(self):
        """Запуск координатора"""
        self.running = True
        
        print("=" * 50)
        print("🤖 AI NETWORK COORDINATOR")
        print("=" * 50)
        print(f"📍 Адрес: {VPS_IP}:{self.port}")
        print(f"📡 Порт: {self.port}")
        print("=" * 50)
        
        try:
            # Создаем сервер
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("0.0.0.0", self.port))
            self.server_socket.listen(10)
            self.server_socket.settimeout(1)
            
            print(f"✅ Сервер запущен на порту {self.port}")
            print("👷 Ожидание подключений...")
            
            # Запускаем фоновые потоки
            cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            cleanup_thread.start()
            
            assigner_thread = threading.Thread(target=self._task_assigner_loop, daemon=True)
            assigner_thread.start()
            
            # Основной цикл accept
            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    
                    # Запускаем обработчик в отдельном потоке
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
                        print(f"❌ Ошибка accept: {e}")
            
        except Exception as e:
            print(f"❌ Ошибка сервера: {e}")
        finally:
            self.running = False
            if self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass
            print("👋 Координатор остановлен")

# ========== РАБОЧИЙ ==========
class SimpleWorker:
    """Простой рабочий узел"""
    
    def __init__(self, host: str = VPS_IP, port: int = PORT, name: str = None):
        self.host = host
        self.port = port
        self.name = name or f"Worker_{random.randint(1000, 9999)}"
        self.worker_id = None
        self.running = False
    
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
                    "checksum": hashlib.md5(str(result).encode()).hexdigest()[:8]
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
                    "worker": self.name
                }
            
            else:
                return {
                    "status": "error",
                    "message": f"Unknown task type: {task_type}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _send_json(self, sock: socket.socket, data: Dict) -> bool:
        """Отправить JSON"""
        try:
            sock.sendall(json.dumps(data).encode())
            return True
        except:
            return False
    
    def _receive_json(self, sock: socket.socket) -> Optional[Dict]:
        """Получить JSON"""
        try:
            sock.settimeout(2)
            data = sock.recv(4096)
            if data:
                return json.loads(data.decode())
        except:
            pass
        return None
    
    def start(self):
        """Запуск рабочего"""
        self.running = True
        
        print(f"👷 Рабочий: {self.name}")
        print(f"📡 Подключение к {self.host}:{self.port}")
        print("=" * 50)
        
        reconnect_delay = 2
        
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                
                print("Подключение...")
                sock.connect((self.host, self.port))
                
                print("✅ Подключено!")
                
                # Регистрируемся
                self._send_json(sock, {
                    "type": "register",
                    "name": self.name,
                    "timestamp": time.time()
                })
                
                # Основной цикл
                last_heartbeat = time.time()
                
                while self.running:
                    current_time = time.time()
                    
                    # Отправляем heartbeat каждые 20 сек
                    if current_time - last_heartbeat > 20:
                        if self._send_json(sock, {
                            "type": "heartbeat",
                            "timestamp": current_time
                        }):
                            last_heartbeat = current_time
                    
                    # Читаем сообщения
                    message = self._receive_json(sock)
                    
                    if message:
                        msg_type = message.get("type")
                        
                        if msg_type == "welcome":
                            print(f"📡 {message.get('message')}")
                        
                        elif msg_type == "registered":
                            self.worker_id = message.get("worker_id")
                            print(f"✅ Зарегистрирован как {message.get('name')}")
                            print(f"🆔 ID: {self.worker_id}")
                        
                        elif msg_type == "task":
                            # Получили задачу!
                            task_id = message.get("task_id")
                            task_type = message.get("task_type")
                            task_data = message.get("data", {})
                            
                            print(f"📥 Задача {task_id}: {task_type}")
                            
                            # Выполняем
                            result = self._process_task(task_type, task_data)
                            
                            # Отправляем результат
                            self._send_json(sock, {
                                "type": "task_result",
                                "task_id": task_id,
                                "result": result,
                                "timestamp": time.time()
                            })
                            
                            if result.get("status") == "success":
                                exec_time = result.get("execution_time", 0)
                                print(f"✅ Выполнено за {exec_time:.3f} сек")
                            else:
                                print(f"❌ Ошибка: {result.get('message')}")
                        
                        elif msg_type == "heartbeat_ack":
                            # Heartbeat подтвержден
                            pass
                    
                    elif message is None:
                        # Таймаут - нормально, продолжаем
                        continue
                
                sock.close()
                
            except ConnectionRefusedError:
                print(f"❌ Сервер недоступен. Повтор через {reconnect_delay} сек...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, 30)
                
            except socket.timeout:
                print(f"❌ Таймаут. Повтор через {reconnect_delay} сек...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, 30)
                
            except KeyboardInterrupt:
                print("\n👋 Остановка...")
                self.running = False
                break
                
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, 30)
        
        print("👷 Рабочий остановлен")

# ========== ПРОСТОЙ КЛИЕНТ ==========
class SimpleClient:
    """Простой клиент для отправки задач"""
    
    @staticmethod
    def submit_task(host: str = VPS_IP, port: int = PORT, 
                   task_type: str = "matrix_mult", task_data: Dict = None) -> Optional[str]:
        """Отправить задачу"""
        if task_data is None:
            task_data = {"size": 10} if task_type == "matrix_mult" else {"numbers": 1000}
        
        try:
            print(f"🔗 Подключение к {host}:{port}...")
            
            # Очень простое подключение
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  # Короткий таймаут
            
            sock.connect((host, port))
            
            # Сразу отправляем задачу
            message = {
                "type": "submit_task",
                "task_type": task_type,
                "data": task_data,
                "timestamp": time.time()
            }
            
            sock.sendall(json.dumps(message).encode())
            print("📨 Задача отправлена")
            
            # Ждем ответ
            sock.settimeout(2)
            try:
                response = sock.recv(4096)
                if response:
                    result = json.loads(response.decode())
                    if result.get("type") == "task_created":
                        task_id = result.get("task_id")
                        print(f"✅ Задача создана: {task_id}")
                        sock.close()
                        return task_id
                    else:
                        print(f"❌ Ответ: {result}")
                else:
                    print("❌ Нет ответа от сервера")
            except socket.timeout:
                print("⏰ Таймаут ожидания ответа")
            except Exception as e:
                print(f"❌ Ошибка чтения: {e}")
            
            sock.close()
            return None
            
        except socket.timeout:
            print("❌ Таймаут подключения")
            return None
        except ConnectionRefusedError:
            print("❌ Сервер недоступен")
            return None
        except Exception as e:
            print(f"❌ Ошибка: {type(e).__name__}: {e}")
            return None
    
    @staticmethod
    def get_stats(host: str = VPS_IP, port: int = PORT) -> Optional[Dict]:
        """Получить статистику"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((host, port))
            
            sock.sendall(json.dumps({
                "type": "get_stats",
                "timestamp": time.time()
            }).encode())
            
            sock.settimeout(2)
            response = sock.recv(4096)
            sock.close()
            
            if response:
                return json.loads(response.decode())
            
            return None
            
        except:
            return None
    
    @staticmethod
    def get_tasks(host: str = VPS_IP, port: int = PORT) -> Optional[Dict]:
        """Получить список задач"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((host, port))
            
            sock.sendall(json.dumps({
                "type": "get_tasks",
                "timestamp": time.time()
            }).encode())
            
            sock.settimeout(2)
            response = sock.recv(4096)
            sock.close()
            
            if response:
                return json.loads(response.decode())
            
            return None
            
        except:
            return None

# ========== ГЛАВНАЯ ФУНКЦИЯ ==========
def main():
    parser = argparse.ArgumentParser(
        description="🚀 AI Network - Простая децентрализованная сеть",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--coordinator', action='store_true',
                       help='Запустить координатор')
    parser.add_argument('--worker', action='store_true',
                       help='Запустить рабочий узел')
    parser.add_argument('--submit', nargs='?', const='matrix_mult',
                       help='Отправить задачу (matrix_mult или calculation)')
    parser.add_argument('--stats', action='store_true',
                       help='Показать статистику')
    parser.add_argument('--tasks', action='store_true',
                       help='Показать список задач')
    parser.add_argument('--host', default=VPS_IP,
                       help=f'Адрес координатора (по умолчанию: {VPS_IP})')
    parser.add_argument('--port', type=int, default=PORT,
                       help=f'Порт (по умолчанию: {PORT})')
    parser.add_argument('--name', 
                       help='Имя рабочего')
    parser.add_argument('--size', type=int, default=10,
                       help='Размер матрицы (для matrix_mult)')
    parser.add_argument('--numbers', type=int, default=1000,
                       help='Количество чисел (для calculation)')
    
    args = parser.parse_args()
    
    if args.coordinator:
        # Запуск координатора
        coordinator = SimpleCoordinator(port=args.port)
        coordinator.start()
    
    elif args.worker:
        # Запуск рабочего
        worker = SimpleWorker(
            host=args.host,
            port=args.port,
            name=args.name
        )
        worker.start()
    
    elif args.submit:
        # Отправка задачи
        task_type = args.submit
        task_data = {}
        
        if task_type == "matrix_mult":
            task_data = {"size": args.size}
        elif task_type == "calculation":
            task_data = {"numbers": args.numbers}
        else:
            print(f"❌ Неизвестный тип задачи: {task_type}")
            print("   Доступно: matrix_mult, calculation")
            return
        
        print(f"📨 Отправка задачи '{task_type}'...")
        task_id = SimpleClient.submit_task(
            host=args.host,
            port=args.port,
            task_type=task_type,
            task_data=task_data
        )
        
        if task_id:
            print(f"✅ Успешно! ID задачи: {task_id}")
            print(f"📊 Проверить: python ai_network.py --tasks --host {args.host}")
        else:
            print("❌ Не удалось отправить задачу")
    
    elif args.stats:
        # Показать статистику
        stats_data = SimpleClient.get_stats(host=args.host, port=args.port)
        
        if stats_data and stats_data.get("type") == "stats":
            stats = stats_data.get("stats", {})
            print("📊 СТАТИСТИКА СЕТИ:")
            print(f"   Рабочих онлайн: {stats.get('workers', 0)}")
            print(f"   Всего задач: {stats.get('tasks_total', 0)}")
            print(f"   Ожидают: {stats.get('tasks_pending', 0)}")
            print(f"   Выполняются: {stats.get('tasks_running', 0)}")
            print(f"   Завершено: {stats.get('tasks_completed', 0)}")
            print(f"   Ошибок: {stats.get('tasks_failed', 0)}")
            print(f"   В очереди: {stats.get('queue', 0)}")
            if stats.get('timestamp'):
                print(f"   Время: {time.strftime('%H:%M:%S', time.localtime(stats['timestamp']))}")
        else:
            print("❌ Не удалось получить статистику")
    
    elif args.tasks:
        # Показать задачи
        tasks_data = SimpleClient.get_tasks(host=args.host, port=args.port)
        
        if tasks_data and tasks_data.get("type") == "tasks_list":
            tasks = tasks_data.get("tasks", [])
            print(f"📝 ЗАДАЧИ ({len(tasks)}):")
            
            for task in tasks:
                status_icons = {
                    "pending": "⏳",
                    "running": "🔄", 
                    "completed": "✅",
                    "failed": "❌"
                }
                
                icon = status_icons.get(task.get("status"), "❓")
                task_id_short = task.get("id", "?")[:8]
                task_type = task.get("type", "?")
                status = task.get("status", "?")
                
                print(f"  {icon} [{task_id_short}] {task_type} - {status}")
                
                if task.get("worker_id"):
                    print(f"     ↳ Рабочий: {task.get('worker_id', '?')[:8]}")
        else:
            print("❌ Не удалось получить список задач")
    
    else:
        # Показать справку
        print("=" * 60)
        print("🤖 AI NETWORK - ПРОСТАЯ ДЕЦЕНТРАЛИЗОВАННАЯ СЕТЬ")
        print("=" * 60)
        print()
        print("КОМАНДЫ:")
        print("  --coordinator           Запустить координатор")
        print("  --worker                Запустить рабочий узел")
        print("  --submit [тип]          Отправить задачу")
        print("  --stats                 Показать статистику")
        print("  --tasks                 Показать список задач")
        print()
        print("ПРИМЕРЫ:")
        print(f"  1. Запуск координатора:")
        print(f"     python ai_network.py --coordinator --port {PORT}")
        print()
        print(f"  2. Подключение рабочего:")
        print(f"     python ai_network.py --worker --host {VPS_IP} --name 'MyPC'")
        print()
        print(f"  3. Отправить задачу умножения матриц:")
        print(f"     python ai_network.py --submit matrix_mult --size 15")
        print()
        print(f"  4. Отправить вычислительную задачу:")
        print(f"     python ai_network.py --submit calculation --numbers 5000")
        print()
        print(f"  5. Показать статистику:")
        print(f"     python ai_network.py --stats --host {VPS_IP}")
        print()
        print(f"  6. Показать задачи:")
        print(f"     python ai_network.py --tasks --host {VPS_IP}")
        print()
        print(f"📡 Сервер: {VPS_IP}:{PORT}")
        print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Программа завершена")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
