"""
logger.py — Affichage console coloré + écriture dans download_log.txt
"""
import colorama
from colorama import Fore, Style
from datetime import datetime

colorama.init(autoreset=True)

LOG_FILE = "download_log.txt"


def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _write(line):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_info(msg):
    line = f"[{_timestamp()}] INFO  | {msg}"
    print(Fore.CYAN + line)
    _write(line)


def log_success(msg):
    line = f"[{_timestamp()}] OK    | {msg}"
    print(Fore.GREEN + Style.BRIGHT + line)
    _write(line)


def log_skip(msg):
    line = f"[{_timestamp()}] SKIP  | {msg}"
    print(Fore.YELLOW + line)
    _write(line)


def log_error(msg):
    line = f"[{_timestamp()}] ERROR | {msg}"
    print(Fore.RED + Style.BRIGHT + line)
    _write(line)


def log_separator():
    line = "=" * 70
    print(Style.DIM + line)
    _write(line)
