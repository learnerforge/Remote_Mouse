import os
import sys
import subprocess
import threading
import time
import socket as sock_lib

try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    class Fore:
        GREEN = CYAN = YELLOW = RED = MAGENTA = BLUE = WHITE = LIGHTBLACK_EX = ''
        RESET = ''
    class Style:
        RESET_ALL = ''

BANNER = f"""
{Fore.GREEN}+---------------------------------------+
|       Remote Mouse  v1.0              |
|       Terminal Control Panel          |
+---------------------------------------+{Style.RESET_ALL}
  Type '{Fore.CYAN}help{Style.RESET_ALL}' for commands     '{Fore.YELLOW}q{Style.RESET_ALL}' to quit
{Fore.LIGHTBLACK_EX}-----------------------------------------{Style.RESET_ALL}
"""

EVENT_LOG_FILE = 'events.log'
TUNNEL_URL_FILE = '.tunnel_url'

server_proc = None

def colorize(line):
    if line.startswith('>'):
        return f"{Fore.GREEN}{line}{Style.RESET_ALL}"
    elif line.startswith('*'):
        return f"{Fore.CYAN}{line}{Style.RESET_ALL}"
    elif line.startswith('-'):
        return f"{Fore.MAGENTA}{line}{Style.RESET_ALL}"
    return f"{Fore.LIGHTBLACK_EX}{line}{Style.RESET_ALL}"

def get_local_ip():
    s = sock_lib.socket(sock_lib.AF_INET, sock_lib.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_tunnel_url():
    if os.path.exists(TUNNEL_URL_FILE):
        with open(TUNNEL_URL_FILE) as f:
            return f.read().strip()
    return None

def cmd_help():
    print(f"""
  {Fore.CYAN}Commands:{Style.RESET_ALL}
    {Fore.GREEN}status{Style.RESET_ALL}  (st)   Server state, IP, tunnel URL
    {Fore.GREEN}log{Style.RESET_ALL}     (l)    Show last 50 action logs
    {Fore.GREEN}clear{Style.RESET_ALL}   (cls)  Clear screen
    {Fore.GREEN}help{Style.RESET_ALL}    (h)    Show this help
    {Fore.GREEN}exit{Style.RESET_ALL}    (q)    Stop server and exit
""")

def cmd_status():
    tunnel = get_tunnel_url()
    ip = get_local_ip()
    state = f"{Fore.GREEN}RUNNING{Style.RESET_ALL}" if server_proc and server_proc.poll() is None else f"{Fore.RED}STOPPED{Style.RESET_ALL}"
    print(f"""
  {Fore.CYAN}Server Status:{Style.RESET_ALL}
    State:    {state}
    Local:    http://{ip}:5000
    Port:     5000
""")
    if tunnel:
        print(f"    Tunnel:   {Fore.GREEN}{tunnel}{Style.RESET_ALL}")
    else:
        print(f"    Tunnel:   {Fore.YELLOW}Not active (local only){Style.RESET_ALL}")

def cmd_log():
    if not os.path.exists(EVENT_LOG_FILE):
        print(f"  {Fore.YELLOW}No log file yet.{Style.RESET_ALL}")
        return
    with open(EVENT_LOG_FILE) as f:
        lines = f.read().strip().splitlines()
    if not lines:
        print(f"  {Fore.YELLOW}No logs yet.{Style.RESET_ALL}")
        return
    print(f"  {Fore.LIGHTBLACK_EX}Last {min(len(lines), 50)} events:{Style.RESET_ALL}")
    for line in lines[-50:]:
        print(f"  {colorize(line)}")

def main():
    global server_proc

    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)

    if os.path.exists(EVENT_LOG_FILE):
        os.remove(EVENT_LOG_FILE)

    import tempfile
    log_tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), EVENT_LOG_FILE)
    server_proc = subprocess.Popen(
        [sys.executable, '-u', 'server.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

    def reader():
        for line in iter(server_proc.stdout.readline, ''):
            line = line.rstrip('\n\r')
            if line:
                print(f"  {colorize(line)}")
                with open(log_tmp, 'a') as f:
                    f.write(line + '\n')

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    time.sleep(2)

    try:
        while True:
            try:
                cmd = input(f"\n{Fore.GREEN}> {Style.RESET_ALL}").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if cmd in ('q', 'quit', 'exit'):
                break
            elif cmd in ('h', 'help'):
                cmd_help()
            elif cmd in ('st', 'status'):
                cmd_status()
            elif cmd in ('l', 'log'):
                cmd_log()
            elif cmd in ('cls', 'clear'):
                os.system('cls' if os.name == 'nt' else 'clear')
                print(BANNER)
            elif cmd == '':
                continue
            else:
                print(f"  {Fore.YELLOW}Unknown: '{cmd}'. Type 'help'{Style.RESET_ALL}")
    finally:
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
            server_proc.wait(timeout=5)
        print(f"\n  {Fore.RED}Server stopped.{Style.RESET_ALL}")

if __name__ == '__main__':
    main()
