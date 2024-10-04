import subprocess
import time
import socket
import sys
from win32 import win32gui
import win32con
import keyboard
import threading
import requests
import os
import logging

vpn_name = "mw"
logging.getLogger().addHandler(logging.NullHandler())
auto_reconnect = True

def create_no_window():
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return startupinfo

def hide_console():
    console_window = win32gui.GetForegroundWindow()
    win32gui.ShowWindow(console_window, win32con.SW_HIDE)

def toggle_console():
    console_window = win32gui.GetForegroundWindow()
    if win32gui.IsWindowVisible(console_window):
        win32gui.ShowWindow(console_window, win32con.SW_HIDE)
    else:
        win32gui.ShowWindow(console_window, win32con.SW_SHOW)

def is_vpn_connected():
    try:
        output = subprocess.check_output('rasdial', universal_newlines=True, startupinfo=create_no_window())
        if vpn_name in output:
            response = requests.get('https://api.ipify.org', timeout=5)
            return response.status_code == 200
        return False
    except (subprocess.CalledProcessError, requests.RequestException):
        return False

def connect_vpn(con_name):
    if not is_vpn_connected():
        try:
            subprocess.run(f'rasdial "{con_name}"', shell=True, check=True, startupinfo=create_no_window())
            time.sleep(5)
            if is_vpn_connected():
                logging.info(f"VPN {con_name} подключен")
            else:
                logging.warning(f"Не удалось подключиться к VPN {con_name}")
        except subprocess.CalledProcessError:
            logging.error(f"Ошибка при попытке подключения к VPN {con_name}")

def disconnect_vpn(con_name):
    try:
        subprocess.run(f'rasdial "{con_name}" /disconnect', shell=True, check=True, startupinfo=create_no_window())
        logging.info(f"VPN {con_name} отключен")
    except subprocess.CalledProcessError:
        logging.error(f"Ошибка при попытке отключения VPN {con_name}")

def disconnect_vpn_and_stop_auto_reconnect(con_name):
    global auto_reconnect
    disconnect_vpn(con_name)
    auto_reconnect = False
    logging.info(f"VPN {con_name} отключен и автоматическое переподключение остановлено")

def connect_vpn_and_start_auto_reconnect(con_name):
    global auto_reconnect
    connect_vpn(con_name)
    auto_reconnect = True
    logging.info(f"VPN {con_name} подключен и автоматическое переподключение запущено")

def vpn_rec(con_name, check_interval=10):
    global auto_reconnect
    while True:
        try:
            if auto_reconnect and not is_vpn_connected():
                logging.info(f"VPN {con_name} отключен. Попытка переподключения...")
                disconnect_vpn(con_name)
                time.sleep(5)
                connect_vpn(con_name)
            elif is_vpn_connected():
                logging.info(f"VPN {con_name} подключен")
        except Exception as e:
            logging.error(f"Ошибка в цикле проверки VPN: {str(e)}")
        time.sleep(check_interval)

def run_script_without_console():
    script_path = os.path.abspath(__file__)
    subprocess.Popen(["pythonw", script_path], creationflags=subprocess.CREATE_NO_WINDOW)
    sys.exit()

def main():
    global auto_reconnect
    if sys.executable.endswith("python.exe"):
        run_script_without_console()
        return

    hide_console()

    logging.info(f"Скрипт запущен {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Инициализация потока VPN и горячих клавиш
    vpn_thread = threading.Thread(target=vpn_rec, args=(vpn_name,))
    vpn_thread.daemon = True
    vpn_thread.start()

    keyboard.add_hotkey('ctrl+shift+q', toggle_console)
    keyboard.add_hotkey('ctrl+shift+x', lambda: disconnect_vpn_and_stop_auto_reconnect(vpn_name))
    keyboard.add_hotkey('ctrl+shift+z', lambda: connect_vpn_and_start_auto_reconnect(vpn_name))

    # Проверка и подключение VPN после инициализации
    if not is_vpn_connected():
        connect_vpn(vpn_name)

    keyboard.wait()

if __name__ == "__main__":
    main()