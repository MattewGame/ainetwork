#!/usr/bin/env python3
"""
🚀 AI Network - УЛЬТРАПРОСТАЯ РАБОЧАЯ ВЕРСИЯ
Все работает через один порт 8888
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

# ========== КООРДИНАТОР ==========
class SimpleCoordinator:
    """Упрощенный координатор - отправляет ответ МГНОВЕННО"""
    
    def __init__(self, port: int = PORT):
        self.port = port
        self.workers = {}
        self.tasks = {}
        self.task_queue = []
        self.lock = threading.RLock()
        self.running = False
        self.server_socket = None
        
        print(f"🚀 Координатор на порту {port}")
    
    def _send_instant_reply(self, conn: socket.socket, data: Dict):
        """Отправить ответ и НЕМЕДЛЕННО закрыть соединение"""
        try:
            json_str = json.dumps(data)
            conn.sendall(json_str.encode())
        except Exception as e:
            print(f"❌ Ошибка отправки ответа: {e}")
            pass
    
    def _handle_connection_fast(self, conn: socket.socket, addr: tuple):
        """Быстрая обработка подключения - ответ и закрытие"""
        client_addr = f"{addr[0]}:{addr[1]}"
        print(f"🔗 Новое подключение от {client_addr}")
        
        try:
            # Читаем запрос с увеличенным таймаутом
            conn.settimeout(30)  # Увеличен таймаут чтения
            data = conn.recv(4096)
            
            if not data:
                print(f"⚠️  Пустые данные от {client_addr}")
                conn.close()
                return
            
            try:
                message = json.loads(data.decode())
                msg_type = message.get("type")
                
                print(f"📨 Запрос '{msg_type}' от {client_addr}")
                
                if msg_type == "submit_task":
                    # КЛИЕНТ ОТПРАВЛЯЕТ ЗАДАЧУ
                    task_type = message.get("task_type", "matrix_mult")
                    task_data = message.get("data", {})
                    client_task_id = message.get("task_id")
                    
                    # Создаем свою задачу
                    task_id = client_task_id or f"task_{int(time.time())}_{random.randint(1000, 9999)}"
                    
                    with self.lock:
                        self.tasks[task_id] = {
                            "id": task_id,
                            "type": task_type,
                            "data": task_data,
                            "status": "pending",
                            "created": time.time(),
                            "worker_id": None,
                            "result": None
                        }
                        self.task_queue.append(task_id)
                    
                    print(f"📨 Задача создана: {task_id} ({task_type})")
                    
                    # МГНОВЕННЫЙ ОТВЕТ
                    self._send_instant_reply(conn, {
                        "type": "task_created",
                        "task_id": task_id,
                        "status": "success",
                        "timestamp": time.time(),
                        "message": "Задача принята"
                    })
                    
                elif msg_type == "register":
                    # РАБОЧИЙ РЕГИСТРИРУЕТСЯ
                    worker_name = message.get("name", "Worker")
                    worker_id = f"worker_{addr[0]}_{addr[1]}_{int(time.time())}"
                    
                    with self.lock:
                        self.workers[worker_id] = {
                            "id": worker_id,
                            "name": worker_name,
                            "addr": addr,
                            "conn": conn,
                            "status": "connected",
                            "last_seen": time.time(),
                            "current_task": None
                        }
                    
                    print(f"👷 Рабочий зарегистрирован: {worker_name} ({worker_id})")
                    
                    # Отправляем приветствие, НО НЕ ЗАКРЫВАЕМ соединение
                    response = {
                        "type": "welcome",
                        "worker_id": worker_id,
                        "name": worker_name,
                        "message": "Добро пожаловать в AI Network!",
                        "timestamp": time.time()
                    }
                    
                    try:
                        conn.sendall(json.dumps(response).encode())
                        print(f"✅ Приветствие отправлено рабочему {worker_id}")
                    except Exception as e:
                        print(f"❌ Ошибка отправки приветствия: {e}")
                        conn.close()
                        return
                    
                    # Запускаем отдельный поток для рабочего
                    worker_thread = threading.Thread(
                        target=self._handle_worker_connection,
                        args=(conn, addr, worker_id),
                        daemon=True
                    )
                    worker_thread.start()
                    print(f"🔄 Поток рабочего запущен для {worker_id}")
                    return  # Не закрываем соединение!
                    
                elif msg_type == "get_stats":
                    # ЗАПРОС СТАТИСТИКИ
                    with self.lock:
                        workers_count = len(self.workers)
                        tasks_total = len(self.tasks)
                        tasks_pending = len([t for t in self.tasks.values() if t.get("status") == "pending"])
                        tasks_running = len([t for t in self.tasks.values() if t.get("status") == "running"])
                        tasks_completed = len([t for t in self.tasks.values() if t.get("status") == "completed"])
                        
                    self._send_instant_reply(conn, {
                        "type": "stats",
                        "stats": {
                            "workers": workers_count,
                            "tasks_total": tasks_total,
                            "tasks_pending": tasks_pending,
                            "tasks_running": tasks_running,
                            "tasks_completed": tasks_completed,
                            "queue": len(self.task_queue),
                            "timestamp": time.time()
                        },
                        "timestamp": time.time()
                    })
                    
                elif msg_type == "get_tasks":
                    # ЗАПРОС СПИСКА ЗАДАЧ
                    tasks_list = []
                    with self.lock:
                        for task_id, task in self.tasks.items():
                            tasks_list.append({
                                "id": task["id"],
                                "type": task["type"],
                                "status": task["status"],
                                "created": task["created"],
                                "worker_id": task["worker_id"]
                            })
                    
                    self._send_instant_reply(conn, {
                        "type": "tasks_list",
                        "tasks": tasks_list,
                        "timestamp": time.time()
                    })
                
                else:
                    # НЕИЗВЕСТНЫЙ ЗАПРОС
                    print(f"⚠️  Неизвестный тип запроса: {msg_type}")
                    self._send_instant_reply(conn, {
                        "type": "error",
                        "message": f"Unknown request type: {msg_type}",
                        "timestamp": time.time()
                    })
                    
            except json.JSONDecodeError as e:
                print(f"❌ Ошибка JSON от {client_addr}: {e}")
                self._send_instant_reply(conn, {
                    "type": "error",
                    "message": "Invalid JSON",
                    "timestamp": time.time()
                })
                
        except socket.timeout:
            print(f"⏰ Таймаут чтения от {client_addr}")
            try:
                conn.close()
            except:
                pass
        except Exception as e:
            print(f"❌ Ошибка обработки от {client_addr}: {type(e).__name__}: {e}")
        finally:
            # Закрываем соединение (кроме рабочих)
            try:
                conn.close()
                print(f"🔌 Соединение закрыто с {client_addr}")
            except:
                pass
    
    def _handle_worker_connection(self, conn: socket.socket, addr: tuple, worker_id: str):
        """Обработка длительного соединения рабочего"""
        print(f"🔄 Рабочий {worker_id} в активном режиме")
        
        try:
            while self.running:
                try:
                    # Читаем сообщения от рабочего
                    conn.settimeout(30)  # Увеличен таймаут
                    data = conn.recv(4096)
                    
                    if not data:
                        print(f"⚠️  Пустые данные от рабочего {worker_id}")
                        break
                    
                    try:
                        message = json.loads(data.decode())
                    except json.JSONDecodeError:
                        print(f"❌ Неверный JSON от рабочего {worker_id}")
                        continue
                    
                    msg_type = message.get("type")
                    
                    if msg_type == "heartbeat":
                        # Обновляем время последней активности
                        with self.lock:
                            if worker_id in self.workers:
                                self.workers[worker_id]["last_seen"] = time.time()
                        
                        # Отправляем подтверждение
                        response = {"type": "heartbeat_ack", "timestamp": time.time()}
                        try:
                            conn.sendall(json.dumps(response).encode())
                        except:
                            break
                    
                    elif msg_type == "task_result":
                        # РЕЗУЛЬТАТ ВЫПОЛНЕНИЯ ЗАДАЧИ
                        task_id = message.get("task_id")
                        result = message.get("result", {})
                        
                        with self.lock:
                            if worker_id in self.workers:
                                self.workers[worker_id]["current_task"] = None
                                self.workers[worker_id]["last_seen"] = time.time()
                            
                            if task_id in self.tasks:
                                task = self.tasks[task_id]
                                
                                if result.get("status") == "success":
                                    task["status"] = "completed"
                                    task["result"] = result
                                    print(f"✅ Задача {task_id} выполнена рабочим {worker_id}")
                                else:
                                    task["status"] = "failed"
                                    task["result"] = result
                                    print(f"❌ Задача {task_id} провалена рабочим {worker_id}")
                        
                        # Пытаемся назначить следующую задачу
                        self._assign_tasks_to_worker(worker_id, conn)
                    
                    elif msg_type == "ready":
                        # РАБОЧИЙ ГОТОВ К ВЫПОЛНЕНИЮ ЗАДАЧ
                        print(f"👌 Рабочий {worker_id} готов к работе")
                        self._assign_tasks_to_worker(worker_id, conn)
                    
                    elif msg_type == "pong":
                        # Ответ на ping
                        with self.lock:
                            if worker_id in self.workers:
                                self.workers[worker_id]["last_seen"] = time.time()
                    
                except socket.timeout:
                    # Отправляем heartbeat запрос
                    try:
                        ping_msg = json.dumps({
                            "type": "ping",
                            "timestamp": time.time()
                        }).encode()
                        conn.sendall(ping_msg)
                        print(f"📡 Ping отправлен рабочему {worker_id}")
                    except Exception as e:
                        print(f"❌ Ошибка ping рабочему {worker_id}: {e}")
                        break
                    continue
                except ConnectionResetError:
                    print(f"🔌 Соединение сброшено рабочим {worker_id}")
                    break
                except Exception as e:
                    print(f"❌ Ошибка чтения от рабочего {worker_id}: {type(e).__name__}: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Ошибка рабочего {worker_id}: {type(e).__name__}: {e}")
        finally:
            # Очищаем рабочего
            with self.lock:
                if worker_id in self.workers:
                    worker = self.workers[worker_id]
                    
                    # Возвращаем задачу если есть
                    if worker["current_task"]:
                        task_id = worker["current_task"]
                        if task_id in self.tasks:
                            task = self.tasks[task_id]
                            if task["status"] == "running":
                                task["status"] = "pending"
                                task["worker_id"] = None
                                self.task_queue.insert(0, task_id)
                                print(f"↩️ Задача {task_id} возвращена в очередь (отключен рабочий {worker_id})")
                    
                    del self.workers[worker_id]
                    print(f"🗑️  Рабочий удален: {worker_id}")
            
            try:
                conn.close()
            except:
                pass
            
            print(f"🔌 Рабочий отключен: {worker_id}")
    
    def _assign_tasks_to_worker(self, worker_id: str, conn: socket.socket):
        """Назначить задачу рабочему"""
        with self.lock:
            if worker_id not in self.workers:
                print(f"⚠️  Рабочий {worker_id} не найден")
                return
            
            worker = self.workers[worker_id]
            
            # Если рабочий уже занят
            if worker["current_task"]:
                print(f"⚠️  Рабочий {worker_id} уже занят задачей {worker['current_task']}")
                return
            
            # Ищем pending задачу
            task_to_assign = None
            for task_id in self.task_queue:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    if task["status"] == "pending":
                        task_to_assign = task_id
                        break
            
            if not task_to_assign:
                print(f"ℹ️  Нет задач для рабочего {worker_id}")
                return
            
            # Отправляем задачу
            task = self.tasks[task_to_assign]
            task_message = {
                "type": "task",
                "task_id": task["id"],
                "task_type": task["type"],
                "data": task["data"],
                "timestamp": time.time()
            }
            
            try:
                conn.sendall(json.dumps(task_message).encode())
                task["status"] = "running"
                task["worker_id"] = worker_id
                worker["current_task"] = task["id"]
                
                # Удаляем из очереди
                if task["id"] in self.task_queue:
                    self.task_queue.remove(task["id"])
                
                print(f"🎯 Задача {task['id']} → {worker['name']} ({worker_id})")
            except Exception as e:
                print(f"❌ Ошибка отправки задачи рабочему {worker_id}: {e}")
                # Возвращаем задачу в очередь
                if task["id"] not in self.task_queue:
                    self.task_queue.insert(0, task["id"])
    
    def _cleanup_loop(self):
        """Очистка неактивных рабочих"""
        while self.running:
            time.sleep(30)
            
            current_time = time.time()
            to_remove = []
            
            with self.lock:
                for worker_id, worker in self.workers.items():
                    if current_time - worker["last_seen"] > 90:  # Увеличен таймаут до 90 сек
                        to_remove.append(worker_id)
            
            for worker_id in to_remove:
                print(f"⏰ Удален по таймауту: {worker_id}")
                with self.lock:
                    if worker_id in self.workers:
                        worker = self.workers[worker_id]
                        
                        # Возвращаем задачу
                        if worker["current_task"]:
                            task_id = worker["current_task"]
                            if task_id in self.tasks:
                                task = self.tasks[task_id]
                                if task["status"] == "running":
                                    task["status"] = "pending"
                                    task["worker_id"] = None
                                    self.task_queue.insert(0, task_id)
                        
                        del self.workers[worker_id]
    
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
            
            # Запускаем очистку
            cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            cleanup_thread.start()
            print("🧹 Запущена очистка неактивных рабочих")
            
            # Основной цикл
            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    print(f"🔗 Принято подключение от {addr[0]}:{addr[1]}")
                    
                    # Обрабатываем каждое подключение в отдельном потоке
                    thread = threading.Thread(
                        target=self._handle_connection_fast,
                        args=(conn, addr),
                        daemon=True
                    )
                    thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"❌ Ошибка accept: {type(e).__name__}: {e}")
            
        except Exception as e:
            print(f"❌ Ошибка сервера: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.running = False
            if self.server_socket:
                try:
                    self.server_socket.close()
                    print("🔒 Серверный сокет закрыт")
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
        self.sock = None
    
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
                    "message": f"Unknown task type: {task_type}",
                    "timestamp": time.time()
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": time.time()
            }
    
    def start(self):
        """Запуск рабочего"""
        self.running = True
        
        print("=" * 50)
        print(f"👷 Рабочий: {self.name}")
        print(f"📡 Подключение к {self.host}:{self.port}")
        print("=" * 50)
        
        reconnect_delay = 2
        max_reconnect_delay = 60
        
        while self.running:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(15)  # Увеличен таймаут подключения
                
                print(f"🔗 Подключение к {self.host}:{self.port}...")
                self.sock.connect((self.host, self.port))
                print("✅ Подключение установлено")
                
                # РЕГИСТРАЦИЯ
                register_msg = {
                    "type": "register",
                    "name": self.name,
                    "timestamp": time.time()
                }
                self.sock.sendall(json.dumps(register_msg).encode())
                print("📨 Отправлена регистрация")
                
                # Получаем ответ
                self.sock.settimeout(10)
                response = self.sock.recv(4096)
                
                if response:
                    try:
                        welcome = json.loads(response.decode())
                        if welcome.get("type") == "welcome":
                            self.worker_id = welcome.get("worker_id")
                            print(f"✅ {welcome.get('message')}")
                            print(f"🆔 ID: {self.worker_id}")
                            
                            # Отправляем что готовы к работе
                            self.sock.sendall(json.dumps({
                                "type": "ready",
                                "timestamp": time.time()
                            }).encode())
                            print("👌 Сообщение 'готов' отправлено")
                            
                            # Сброс задержки переподключения
                            reconnect_delay = 2
                            
                            # Основной цикл работы
                            last_heartbeat = time.time()
                            
                            while self.running:
                                try:
                                    current_time = time.time()
                                    
                                    # Heartbeat каждые 25 сек
                                    if current_time - last_heartbeat > 25:
                                        try:
                                            self.sock.sendall(json.dumps({
                                                "type": "heartbeat",
                                                "timestamp": current_time
                                            }).encode())
                                            print(f"💓 Heartbeat отправлен")
                                            last_heartbeat = current_time
                                        except:
                                            print("❌ Ошибка отправки heartbeat")
                                            break
                                    
                                    # Читаем сообщения с увеличенным таймаутом
                                    self.sock.settimeout(5)
                                    data = self.sock.recv(4096)
                                    
                                    if data:
                                        try:
                                            message = json.loads(data.decode())
                                            msg_type = message.get("type")
                                            
                                            if msg_type == "task":
                                                # ПОЛУЧИЛИ ЗАДАЧУ!
                                                task_id = message.get("task_id")
                                                task_type = message.get("task_type")
                                                task_data = message.get("data", {})
                                                
                                                print(f"📥 Получена задача {task_id}: {task_type}")
                                                print(f"⚙️  Выполнение...")
                                                
                                                # Выполняем
                                                result = self._process_task(task_type, task_data)
                                                
                                                # Отправляем результат
                                                try:
                                                    self.sock.sendall(json.dumps({
                                                        "type": "task_result",
                                                        "task_id": task_id,
                                                        "result": result,
                                                        "timestamp": time.time()
                                                    }).encode())
                                                    
                                                    if result.get("status") == "success":
                                                        exec_time = result.get("execution_time", 0)
                                                        print(f"✅ Выполнено за {exec_time:.3f} сек")
                                                    else:
                                                        print(f"❌ Ошибка выполнения: {result.get('message')}")
                                                except:
                                                    print("❌ Ошибка отправки результата")
                                                    break
                                            
                                            elif msg_type == "heartbeat_ack":
                                                # OK
                                                pass
                                            
                                            elif msg_type == "ping":
                                                # Отвечаем на ping
                                                self.sock.sendall(json.dumps({
                                                    "type": "pong",
                                                    "timestamp": time.time()
                                                }).encode())
                                                print("🏓 Pong отправлен")
                                        
                                        except json.JSONDecodeError:
                                            print("❌ Неверный JSON от сервера")
                                            continue
                                    
                                except socket.timeout:
                                    # Таймаут чтения - нормально, продолжаем цикл
                                    continue
                                except ConnectionResetError:
                                    print("🔌 Соединение сброшено сервером")
                                    break
                                except Exception as e:
                                    print(f"❌ Ошибка в цикле работы: {type(e).__name__}: {e}")
                                    break
                        
                        else:
                            print(f"❌ Неверный ответ сервера: {welcome}")
                            reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
                    
                    except json.JSONDecodeError:
                        print("❌ Неверный JSON от сервера")
                        reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
                
                self.sock.close()
                self.sock = None
                
                if not self.running:
                    break
                    
                print(f"🔌 Соединение закрыто. Повтор через {reconnect_delay} сек...")
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
                print("\n👋 Остановка...")
                self.running = False
                if self.sock:
                    try:
                        self.sock.close()
                    except:
                        pass
                break
                
            except Exception as e:
                print(f"❌ Ошибка подключения: {type(e).__name__}: {e}")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
        
        print("👷 Рабочий остановлен")

# ========== ПРОСТОЙ КЛИЕНТ ==========
class SimpleClient:
    """Простой клиент для отправки задач"""
    
    @staticmethod
    def submit_task(host: str = VPS_IP, port: int = PORT, 
                   task_type: str = "matrix_mult", task_data: Dict = None) -> Optional[str]:
        """Отправить задачу - УПРОЩЕННЫЙ ВАРИАНТ"""
        if task_data is None:
            task_data = {"size": 10} if task_type == "matrix_mult" else {"numbers": 1000}
        
        try:
            print(f"🔗 Подключение к {host}:{port}...")
            
            # Простое подключение
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)  # Увеличен таймаут
            
            sock.connect((host, port))
            print("✅ Подключение установлено")
            
            # Генерируем ID задачи
            task_id = f"task_{int(time.time())}_{random.randint(1000, 9999)}"
            
            # Отправляем задачу
            message = {
                "type": "submit_task",
                "task_id": task_id,
                "task_type": task_type,
                "data": task_data,
                "timestamp": time.time()
            }
            
            sock.sendall(json.dumps(message).encode())
            print(f"📨 Задача отправлена: {task_id}")
            
            # Ждем ответ
            sock.settimeout(10)  # Увеличен таймаут
            response = sock.recv(4096)
            sock.close()
            
            if response:
                try:
                    result = json.loads(response.decode())
                    if result.get("type") == "task_created":
                        returned_id = result.get("task_id", task_id)
                        print(f"✅ Задача создана: {returned_id}")
                        return returned_id
                    else:
                        print(f"❌ Ответ сервера: {result.get('type')}")
                        print(f"   Сообщение: {result.get('message', 'Нет деталей')}")
                        return None
                except json.JSONDecodeError:
                    print("❌ Неверный JSON от сервера")
                    return None
            else:
                print("❌ Нет ответа от сервера")
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
            sock.settimeout(10)
            sock.connect((host, port))
            
            sock.sendall(json.dumps({
                "type": "get_stats",
                "timestamp": time.time()
            }).encode())
            
            sock.settimeout(10)
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
            sock.settimeout(10)
            sock.connect((host, port))
            
            sock.sendall(json.dumps({
                "type": "get_tasks",
                "timestamp": time.time()
            }).encode())
            
            sock.settimeout(10)
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
            print("=" * 40)
            print("📊 СТАТИСТИКА СЕТИ:")
            print("=" * 40)
            print(f"   Рабочих онлайн: {stats.get('workers', 0)}")
            print(f"   Всего задач: {stats.get('tasks_total', 0)}")
            print(f"   Ожидают: {stats.get('tasks_pending', 0)}")
            print(f"   Выполняются: {stats.get('tasks_running', 0)}")
            print(f"   Завершено: {stats.get('tasks_completed', 0)}")
            print(f"   В очереди: {stats.get('queue', 0)}")
            print(f"   Обновлено: {time.strftime('%H:%M:%S', time.localtime(stats.get('timestamp', time.time())))}")
            print("=" * 40)
        else:
            print("❌ Не удалось получить статистику")
    
    elif args.tasks:
        # Показать задачи
        tasks_data = SimpleClient.get_tasks(host=args.host, port=args.port)
        
        if tasks_data and tasks_data.get("type") == "tasks_list":
            tasks = tasks_data.get("tasks", [])
            print(f"=" * 60)
            print(f"📝 ЗАДАЧИ ({len(tasks)}):")
            print(f"=" * 60)
            
            if not tasks:
                print("   Нет задач")
            else:
                for task in tasks:
                    status_icons = {
                        "pending": "⏳",
                        "running": "🔄", 
                        "completed": "✅",
                        "failed": "❌"
                    }
                    
                    icon = status_icons.get(task.get("status"), "❓")
                    task_id = task.get("id", "?")
                    task_type = task.get("type", "?")
                    status = task.get("status", "?")
                    worker_id = task.get("worker_id", "нет")
                    
                    # Форматируем время
                    created_time = task.get("created", time.time())
                    time_str = time.strftime("%H:%M:%S", time.localtime(created_time))
                    
                    print(f"  {icon} {task_id}")
                    print(f"     Тип: {task_type}, Статус: {status}")
                    print(f"     Рабочий: {worker_id}, Создана: {time_str}")
                    print()
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
