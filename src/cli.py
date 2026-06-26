import os
import sys
import subprocess
import threading
import time
import socket as sock_lib

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    class Fore:
        GREEN = CYAN = YELLOW = RED = LIGHTBLACK_EX = ''
    class Style:
        RESET_ALL = ''

BANNER = f"""
{Fore.GREEN}+---------------------------------------+
|       Remote Mouse  v1.0.0            |
|       Terminal Control Panel          |
+---------------------------------------+{Style.RESET_ALL}
  Type '{Fore.CYAN}help{Style.RESET_ALL}' for commands     '{Fore.YELLOW}q{Style.RESET_ALL}' to quit
{Fore.LIGHTBLACK_EX}-----------------------------------------{Style.RESET_ALL}"""

SETUP_URL = 'http://localhost:5000/setup'

EVENT_LOG_FILE = os.path.join(PROJECT_ROOT, 'events.log')
TUNNEL_URL_FILE = os.path.join(PROJECT_ROOT, '.tunnel_url')

server_proc = None

def colorize(line):
    if ' ERROR ' in line:
        return f"{Fore.RED}{line}{Style.RESET_ALL}"
    if ' WARN ' in line:
        return f"{Fore.YELLOW}{line}{Style.RESET_ALL}"
    if ' OK ' in line:
        return f"{Fore.GREEN}{line}{Style.RESET_ALL}"
    if ' INFO ' in line:
        return f"{Fore.LIGHTBLACK_EX}{line}{Style.RESET_ALL}"
    return line

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
    {Fore.GREEN}status{Style.RESET_ALL}  (st)       Server state, IP, tunnel URL
    {Fore.GREEN}log{Style.RESET_ALL}     (l / la)   Show errors/warnings; 'la' for all events
    {Fore.GREEN}clear{Style.RESET_ALL}   (cls)      Clear screen
    {Fore.GREEN}help{Style.RESET_ALL}    (h)        Show this help
    {Fore.GREEN}exit{Style.RESET_ALL}    (q)        Stop server and exit
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

def cmd_log(show_all=False):
    if not os.path.exists(EVENT_LOG_FILE):
        print(f"  {Fore.YELLOW}No log file yet.{Style.RESET_ALL}")
        return
    with open(EVENT_LOG_FILE) as f:
        lines = f.read().strip().splitlines()
    if not lines:
        print(f"  {Fore.YELLOW}No logs yet.{Style.RESET_ALL}")
        return
    if show_all:
        shown = lines[-100:]
        print(f"  {Fore.LIGHTBLACK_EX}Last {len(shown)} events:{Style.RESET_ALL}")
        for line in shown:
            print(f"  {colorize(line)}")
    else:
        filtered = [l for l in lines if ' ERROR ' in l or ' WARN ' in l]
        shown = filtered[-100:]
        if not shown:
            print(f"  {Fore.GREEN}No errors or warnings.{Style.RESET_ALL}")
            return
        print(f"  {Fore.LIGHTBLACK_EX}Last {len(shown)} errors/warnings:{Style.RESET_ALL}")
        for line in shown:
            print(f"  {colorize(line)}")

def main():
    global server_proc

    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)

    if os.path.exists(EVENT_LOG_FILE):
        os.remove(EVENT_LOG_FILE)

    server_proc = subprocess.Popen(
        [sys.executable, '-u', os.path.join(PROJECT_ROOT, 'src', 'server.py')],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=PROJECT_ROOT
    )

    def reader():
        for line in iter(server_proc.stdout.readline, ''):
            line = line.rstrip('\n\r')
            if line:
                if ' INFO ' not in line:
                    print(f"  {colorize(line)}")
                with open(EVENT_LOG_FILE, 'a') as f:
                    f.write(line + '\n')

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    time.sleep(2)

    # Auto-open setup page in browser
    import webbrowser
    print(f"  {Fore.CYAN}Opening setup page...{Style.RESET_ALL}")
    print(f"  {Fore.LIGHTBLACK_EX}If browser doesn't open, visit:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}{SETUP_URL}{Style.RESET_ALL}")
    try:
        webbrowser.open(SETUP_URL)
    except Exception:
        pass

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
                cmd_log(show_all=False)
            elif cmd in ('la', 'log all', 'logall'):
                cmd_log(show_all=True)
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
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()
        print(f"\n  {Fore.RED}Server stopped.{Style.RESET_ALL}")

if __name__ == '__main__':
    main()
