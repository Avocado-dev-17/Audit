import tkinter as tk  # Импорт библиотеки Tkinter для создания графического интерфейса
from tkinter import ttk, scrolledtext, messagebox, filedialog  # Импорт подмодулей Tkinter: ttk для тематизированных виджетов, scrolledtext для текстовых полей с прокруткой, messagebox для диалоговых окон сообщений, filedialog для диалогов выбора файлов/папок
import threading  # Импорт модуля для работы с потоками, чтобы мониторинг не блокировал основной интерфейс
from pynput import keyboard, mouse  # Импорт библиотеки pynput для отслеживания нажатий клавиатуры и кликов мыши
import time  # Импорт модуля time для работы с временем (например, форматирование timestamp в логах)
import logging  # Импорт модуля logging (не используется в этой версии, так как логи не сохраняются автоматически)
import psutil  # Импорт библиотеки psutil для мониторинга системных ресурсов (процессы, ЦПУ, память, сеть)
import platform  # Импорт модуля platform для определения ОС (Windows/Linux) для настройки иконки
import socket  # Импорт модуля socket для работы с сетевыми протоколами (TCP/UDP в мониторинге сети)
import os  # Импорт модуля os для работы с файловыми путями при сохранении логов

class UserAuditApp:  # Основной класс приложения для аудита действий пользователя
    def __init__(self, root):  # Инициализатор класса, принимает корневое окно Tkinter
        self.root = root  # Сохранение ссылки на корневое окно
        self.root.title("Аудит действий пользователя")  # Установка заголовка окна
        self.root.geometry("800x500")  # Установка размера окна (800x500 пикселей)
        self.root.configure(bg='#f0f0f0')  # Установка фонового цвета окна (светло-серый)

        # Стили для тематизированных виджетов (ttk)
        self.style = ttk.Style()  # Создание объекта стилей
        self.style.configure("TButton", padding=6, font=("Helvetica", 10))  # Стиль для кнопок: отступы и шрифт
        self.style.configure("TNotebook", background='#f0f0f0')  # Стиль для вкладок: фон
        self.style.configure("TFrame", background='#f0f0f0')  # Стиль для фреймов: фон

        # Флаги и слушатели для мониторинга
        self.running = False  # Флаг, указывающий, запущен ли аудит (по умолчанию выключен)
        self.keyboard_listener = None  # Слушатель клавиатуры (будет инициализирован позже)
        self.mouse_listener = None  # Слушатель мыши (будет инициализирован позже)
        self.resource_monitor_thread = None  # Поток для мониторинга ресурсов (будет инициализирован позже)
        self.previous_processes = {}  # Словарь для хранения предыдущего состояния процессов (PID: имя) для отслеживания изменений

        # Основной контейнер (фрейм) для элементов интерфейса
        self.main_frame = ttk.Frame(self.root)  # Создание фрейма
        self.main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)  # Размещение фрейма с отступами и заполнением пространства

        # Панель кнопок
        self.button_frame = ttk.Frame(self.main_frame)  # Фрейм для кнопок
        self.button_frame.pack(fill=tk.X, pady=5)  # Размещение фрейма с заполнением по горизонтали

        self.start_button = ttk.Button(self.button_frame, text="Начать аудит", command=self.start_audit)  # Кнопка запуска аудита
        self.start_button.pack(side=tk.LEFT, padx=5)  # Размещение кнопки слева с отступом

        self.stop_button = ttk.Button(self.button_frame, text="Остановить аудит", command=self.stop_audit, state=tk.DISABLED)  # Кнопка остановки аудита (изначально отключена)
        self.stop_button.pack(side=tk.LEFT, padx=5)  # Размещение кнопки слева с отступом

        self.clear_button = ttk.Button(self.button_frame, text="Очистить все логи", command=self.clear_logs)  # Кнопка очистки логов
        self.clear_button.pack(side=tk.LEFT, padx=5)  # Размещение кнопки слева с отступом

        self.save_button = ttk.Button(self.button_frame, text="Сохранить логи", command=self.open_save_dialog)  # Кнопка сохранения логов (открывает диалог выбора)
        self.save_button.pack(side=tk.LEFT, padx=5)  # Размещение кнопки слева с отступом

        # Поле поиска
        self.search_frame = ttk.Frame(self.main_frame)  # Фрейм для поля поиска
        self.search_frame.pack(fill=tk.X, pady=5)  # Размещение фрейма с заполнением по горизонтали
        self.search_label = ttk.Label(self.search_frame, text="Поиск:")  # Метка "Поиск:"
        self.search_label.pack(side=tk.LEFT, padx=5)  # Размещение метки слева
        self.search_entry = ttk.Entry(self.search_frame)  # Поле ввода для запроса поиска
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)  # Размещение поля с заполнением пространства
        self.search_button = ttk.Button(self.search_frame, text="Найти", command=self.search_logs)  # Кнопка запуска поиска
        self.search_button.pack(side=tk.LEFT, padx=5)  # Размещение кнопки слева

        # Вкладки (ноутбук)
        self.notebook = ttk.Notebook(self.main_frame)  # Создание ноутбука для вкладок
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)  # Размещение ноутбука с заполнением пространства

        # Создание вкладок
        self.keyboard_tab = ttk.Frame(self.notebook)  # Вкладка для клавиатуры
        self.mouse_tab = ttk.Frame(self.notebook)  # Вкладка для мыши
        self.process_tab = ttk.Frame(self.notebook)  # Вкладка для процессов
        self.resource_tab = ttk.Frame(self.notebook)  # Вкладка для ресурсов
        self.network_tab = ttk.Frame(self.notebook)  # Вкладка для сети

        # Добавление вкладок в ноутбук
        self.notebook.add(self.keyboard_tab, text="Клавиатура")  # Добавление вкладки клавиатуры
        self.notebook.add(self.mouse_tab, text="Мышь")  # Добавление вкладки мыши
        self.notebook.add(self.process_tab, text="Процессы")  # Добавление вкладки процессов
        self.notebook.add(self.resource_tab, text="Ресурсы")  # Добавление вкладки ресурсов
        self.notebook.add(self.network_tab, text="Сеть")  # Добавление вкладки сети

        # Текстовые поля для логов в каждой вкладке
        self.keyboard_log = scrolledtext.ScrolledText(self.keyboard_tab, wrap=tk.WORD, width=90, height=20, font=("Courier", 10))  # Текстовое поле для клавиатуры с прокруткой
        self.keyboard_log.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)  # Размещение с заполнением

        self.mouse_log = scrolledtext.ScrolledText(self.mouse_tab, wrap=tk.WORD, width=90, height=20, font=("Courier", 10))  # Текстовое поле для мыши
        self.mouse_log.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)  # Размещение

        self.process_log = scrolledtext.ScrolledText(self.process_tab, wrap=tk.WORD, width=90, height=20, font=("Courier", 10))  # Текстовое поле для процессов
        self.process_log.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)  # Размещение

        self.resource_log = scrolledtext.ScrolledText(self.resource_tab, wrap=tk.WORD, width=90, height=20, font=("Courier", 10))  # Текстовое поле для ресурсов
        self.resource_log.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)  # Размещение

        self.network_log = scrolledtext.ScrolledText(self.network_tab, wrap=tk.WORD, width=90, height=20, font=("Courier", 10))  # Текстовое поле для сети
        self.network_log.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)  # Размещение

    def log_action(self, log_widget, message):  # Функция для логирования сообщения в указанное текстовое поле
        """Логирование действия только в соответствующую вкладку GUI"""
        log_widget.insert(tk.END, f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")  # Вставка сообщения с timestamp в конец поля
        log_widget.see(tk.END)  # Прокрутка к концу поля для отображения нового сообщения

    def on_key_press(self, key):  # Обработчик нажатия клавиши (из pynput)
        try:
            self.log_action(self.keyboard_log, f"Клавиша нажата: {key.char}")  # Логирование обычной клавиши
        except AttributeError:
            self.log_action(self.keyboard_log, f"Специальная клавиша нажата: {key}")  # Логирование специальной клавиши (например, Shift)

    def on_mouse_click(self, x, y, button, pressed):  # Обработчик клика мыши (из pynput)
        if pressed:  # Логируем только нажатия (не отпускания)
            self.log_action(self.mouse_log, f"Кнопка мыши {button} нажата в ({x}, {y})")  # Логирование клика с координатами

    def monitor_resources(self):  # Функция мониторинга ресурсов в отдельном потоке
        """Мониторинг процессов, ресурсов и сети"""
        while self.running:  # Цикл работает пока аудит запущен
            # Мониторинг процессов (открытые/закрытые)
            current_processes = {}  # Текущий словарь процессов
            for proc in psutil.process_iter(['pid', 'name']):  # Итерация по всем процессам
                try:
                    current_processes[proc.info['pid']] = proc.info['name']  # Сохранение PID и имени
                except (psutil.NoSuchProcess, psutil.AccessDenied):  # Обработка ошибок (процесс исчез или доступ запрещен)
                    pass

            # Проверка новых процессов (открытых)
            for pid, name in current_processes.items():
                if pid not in self.previous_processes:
                    self.log_action(self.process_log, f"Процесс открыт: {name} (PID: {pid})")  # Логирование открытия

            # Проверка закрытых процессов
            for pid, name in self.previous_processes.items():
                if pid not in current_processes:
                    self.log_action(self.process_log, f"Процесс закрыт: {name} (PID: {pid})")  # Логирование закрытия

            self.previous_processes = current_processes  # Обновление предыдущего состояния

            # Мониторинг ЦПУ и памяти
            cpu_usage = psutil.cpu_percent(interval=1)  # Получение использования ЦПУ (за 1 секунду)
            memory = psutil.virtual_memory()  # Получение информации о памяти
            self.log_action(self.resource_log, f"ЦПУ: {cpu_usage}% | Память: {memory.percent}% (Использовано: {memory.used//1024**2} МБ)")  # Логирование

            # Мониторинг сети
            net_io = psutil.net_io_counters()  # Получение статистики сети
            self.log_action(self.network_log, f"Сеть: Отправлено {net_io.bytes_sent//1024} КБ, Получено {net_io.bytes_recv//1024} КБ")  # Логирование трафика

            # Мониторинг активных соединений
            try:
                connections = psutil.net_connections()  # Получение списка соединений
                for conn in connections:  # Итерация по соединениям
                    if conn.status == 'ESTABLISHED' and conn.raddr:  # Только установленные соединения с удаленным адресом
                        remote_ip = conn.raddr.ip  # Удаленный IP
                        remote_port = conn.raddr.port  # Удаленный порт
                        local_port = conn.laddr.port  # Локальный порт
                        protocol = 'TCP' if conn.type == socket.SOCK_STREAM else 'UDP'  # Определение протокола
                        self.log_action(self.network_log, f"Соединение: {protocol} {remote_ip}:{remote_port} (локальный порт: {local_port})")  # Логирование
            except (psutil.AccessDenied, psutil.NoSuchProcess):  # Обработка ошибок доступа
                pass

            time.sleep(5)  # Пауза 5 секунд перед следующей итерацией

    def start_audit(self):  # Функция запуска аудита
        if not self.running:  # Проверка, что аудит не запущен
            self.running = True  # Установка флага
            self.start_button.config(state=tk.DISABLED)  # Отключение кнопки запуска
            self.stop_button.config(state=tk.NORMAL)  # Включение кнопки остановки
            
            # Инициализация списка процессов
            self.previous_processes = {proc.pid: proc.info['name'] for proc in psutil.process_iter(['pid', 'name'])}  # Сбор текущих процессов

            # Запуск слушателей клавиатуры и мыши
            self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)  # Слушатель клавиатуры (только нажатия)
            self.mouse_listener = mouse.Listener(on_click=self.on_mouse_click)  # Слушатель мыши (клики)
            
            threading.Thread(target=self.keyboard_listener.start, daemon=True).start()  # Запуск слушателя клавиатуры в потоке (daemon для автоматического завершения)
            threading.Thread(target=self.mouse_listener.start, daemon=True).start()  # Запуск слушателя мыши в потоке
            
            # Запуск мониторинга ресурсов
            self.resource_monitor_thread = threading.Thread(target=self.monitor_resources, daemon=True)  # Поток мониторинга
            self.resource_monitor_thread.start()  # Запуск потока
            
            # Логирование запуска в каждую вкладку
            self.log_action(self.keyboard_log, "Аудит клавиатуры запущен")
            self.log_action(self.mouse_log, "Аудит мыши запущен")
            self.log_action(self.process_log, "Аудит процессов запущен")
            self.log_action(self.resource_log, "Аудит ресурсов запущен")
            self.log_action(self.network_log, "Аудит сети запущен")

    def stop_audit(self):  # Функция остановки аудита
        if self.running:  # Проверка, что аудит запущен
            self.running = False  # Сброс флага
            self.start_button.config(state=tk.NORMAL)  # Включение кнопки запуска
            self.stop_button.config(state=tk.DISABLED)  # Отключение кнопки остановки
            
            if self.keyboard_listener:  # Остановка слушателя клавиатуры, если существует
                self.keyboard_listener.stop()
            if self.mouse_listener:  # Остановка слушателя мыши, если существует
                self.mouse_listener.stop()
            
            # Логирование остановки в каждую вкладку
            self.log_action(self.keyboard_log, "Аудит клавиатуры остановлен")
            self.log_action(self.mouse_log, "Аудит мыши остановлен")
            self.log_action(self.process_log, "Аудит процессов остановлен")
            self.log_action(self.resource_log, "Аудит ресурсов остановлен")
            self.log_action(self.network_log, "Аудит сети остановлен")

    def clear_logs(self):  # Функция очистки всех логов
        """Очистка всех текстовых полей"""
        for log in [self.keyboard_log, self.mouse_log, self.process_log, self.resource_log, self.network_log]:  # Итерация по всем текстовым полям
            log.delete(1.0, tk.END)  # Удаление содержимого от начала до конца

    def open_save_dialog(self):  # Функция открытия диалога сохранения логов
        """Открытие диалогового окна для выбора логов и директории сохранения"""
        save_dialog = tk.Toplevel(self.root)  # Создание модального окна
        save_dialog.title("Выбор логов для сохранения")  # Заголовок окна
        save_dialog.geometry("300x300")  # Размер окна
        save_dialog.transient(self.root)  # Сделать окно модальным относительно главного
        save_dialog.grab_set()  # Захват фокуса

        ttk.Label(save_dialog, text="Выберите логи для сохранения:").pack(pady=10)  # Метка с инструкцией

        # Флажки для выбора категорий логов (BooleanVar для хранения состояний)
        self.save_keyboard = tk.BooleanVar(value=True)  # Флажок клавиатуры (по умолчанию включен)
        self.save_mouse = tk.BooleanVar(value=True)  # Флажок мыши
        self.save_process = tk.BooleanVar(value=True)  # Флажок процессов
        self.save_resource = tk.BooleanVar(value=True)  # Флажок ресурсов
        self.save_network = tk.BooleanVar(value=True)  # Флажок сети

        # Добавление чекбоксов
        ttk.Checkbutton(save_dialog, text="Клавиатура", variable=self.save_keyboard).pack(anchor="w", padx=20)
        ttk.Checkbutton(save_dialog, text="Мышь", variable=self.save_mouse).pack(anchor="w", padx=20)
        ttk.Checkbutton(save_dialog, text="Процессы", variable=self.save_process).pack(anchor="w", padx=20)
        ttk.Checkbutton(save_dialog, text="Ресурсы", variable=self.save_resource).pack(anchor="w", padx=20)
        ttk.Checkbutton(save_dialog, text="Сеть", variable=self.save_network).pack(anchor="w", padx=20)

        def confirm_save():  # Внутренняя функция подтверждения сохранения
            directory = filedialog.askdirectory(title="Выберите папку для сохранения логов")  # Диалог выбора папки
            if not directory:  # Если папка не выбрана, закрыть диалог
                save_dialog.destroy()
                return

            try:  # Попытка сохранения
                log_files = [  # Список кортежей: (текстовое поле, имя файла, флаг сохранения)
                    (self.keyboard_log, "keyboard.log", self.save_keyboard.get()),
                    (self.mouse_log, "mouse.log", self.save_mouse.get()),
                    (self.process_log, "process.log", self.save_process.get()),
                    (self.resource_log, "resource.log", self.save_resource.get()),
                    (self.network_log, "network.log", self.save_network.get())
                ]

                saved_files = []  # Список сохраненных файлов
                for log_widget, filename, save_flag in log_files:  # Итерация по списку
                    if save_flag:  # Если флаг включен
                        file_path = os.path.join(directory, filename)  # Формирование пути файла
                        with open(file_path, 'w', encoding='utf-8') as f:  # Открытие файла для записи
                            f.write(log_widget.get(1.0, tk.END))  # Запись содержимого поля
                        saved_files.append(filename)  # Добавление в список

                if saved_files:  # Если файлы сохранены
                    messagebox.showinfo("Успех", f"Логи сохранены в {directory}: {', '.join(saved_files)}")  # Сообщение успеха
                else:  # Если ничего не выбрано
                    messagebox.showinfo("Информация", "Логи не выбраны для сохранения")  # Информационное сообщение
                save_dialog.destroy()  # Закрытие диалога
            except Exception as e:  # Обработка ошибок
                messagebox.showerror("Ошибка", f"Не удалось сохранить логи: {str(e)}")  # Сообщение об ошибке
                save_dialog.destroy()  # Закрытие диалога

        ttk.Button(save_dialog, text="Сохранить", command=confirm_save).pack(pady=20)  # Кнопка сохранения
        ttk.Button(save_dialog, text="Отмена", command=save_dialog.destroy).pack()  # Кнопка отмены

    def search_logs(self):  # Функция поиска по логам
        """Поиск по логам в текущей вкладке"""
        search_term = self.search_entry.get().lower()  # Получение запроса поиска (в нижнем регистре)
        if not search_term:  # Если запрос пустой
            messagebox.showwarning("Предупреждение", "Введите запрос для поиска")  # Предупреждение
            return

        # Определяем текущую вкладку
        current_tab = self.notebook.select()  # Получение ID текущей вкладки
        tab_index = self.notebook.index(current_tab)  # Индекс вкладки
        log_widgets = [self.keyboard_log, self.mouse_log, self.process_log, self.resource_log, self.network_log]  # Список текстовых полей
        log_widget = log_widgets[tab_index]  # Текущее поле

        # Сбрасываем предыдущие выделения
        log_widget.tag_remove("highlight", "1.0", tk.END)  # Удаление тега подсветки

        # Получаем текст лога
        content = log_widget.get("1.0", tk.END).lower()  # Текст в нижнем регистре
        lines = content.splitlines()  # Разделение на строки

        # Поиск совпадений
        found = False  # Флаг нахождения
        log_widget.tag_configure("highlight", background="yellow")  # Настройка тега подсветки (желтый фон)
        for i, line in enumerate(lines, 1):  # Итерация по строкам (нумерация с 1)
            if search_term in line:  # Если запрос в строке
                found = True  # Установка флага
                start_pos = f"{i}.0"  # Начало строки
                end_pos = f"{i}.end"  # Конец строки
                log_widget.tag_add("highlight", start_pos, end_pos)  # Добавление тега

        if not found:  # Если ничего не найдено
            messagebox.showinfo("Поиск", f"Совпадений с '{search_term}' не найдено")  # Информационное сообщение

if __name__ == "__main__":  # Если скрипт запущен напрямую (не импортирован)
    root = tk.Tk()  # Создание корневого окна
    # Настройка иконки приложения (для Windows и Linux)
    if platform.system() == "Windows":  # Если ОС Windows
        try:
            root.iconbitmap("img/icon.ico")  # Установка иконки .ico
        except:  # Если ошибка (файл не найден)
            pass  # Игнорировать
    elif platform.system() == "Linux":  # Если ОС Linux
        try:
            root.iconphoto(True, tk.PhotoImage(file="img/icon.png"))  # Установка иконки .png
        except:  # Если ошибка
            pass  # Игнорировать
    app = UserAuditApp(root)  # Создание экземпляра приложения
    root.mainloop()  # Запуск основного цикла Tkinter