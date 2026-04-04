import datetime

# ANSI Colors for Windows Terminal
COLORS = {
    "gateway": "\033[96m",      # Cyan
    "agent": "\033[92m",        # Green
    "llm": "\033[93m",          # Yellow
    "ws": "\033[94m",           # Blue
    "memory": "\033[95m",       # Magenta
    "tools": "\033[97m",        # White
    "error": "\033[1;31m",     # Red Bold
    "warn": "\033[1;33m",      # Yellow Bold
    "reset": "\033[0m"
}

def log(category: str, message: str):
    """
    Kategori berwarna menggunakan ANSI color codes (works di Windows Terminal):
    HH:MM:SS [kategori] pesan
    """
    now = datetime.datetime.now().strftime("%H:%M:%S")
    color = COLORS.get(category.lower(), COLORS["reset"])
    reset = COLORS["reset"]
    
    print(f"{now} {color}[{category.lower():<7}]{reset} {message}")
