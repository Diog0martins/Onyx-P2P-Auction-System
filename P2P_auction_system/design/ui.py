import time
from datetime import datetime

class UI:
    
    # --- ANSI Colors ---
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    GREY    = "\033[90m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"

    # --- Config ---
    SHOW_TIME = True 

    # =========================================================
    #  PART 1: SETUP & HELPERS
    # =========================================================
    
    @staticmethod
    def banner():
        print("\033[2J\033[H")
        print(f"{UI.CYAN}")
        print(r"""
   ____  _   _ __   ____  __
  / __ \| \ | |\ \ / /\ \/ /
 | |  | |  \| | \ V /  >  < 
 | |__| | . ` |  | |  / .  \
  \____/|_| \_|  |_| /_/ \_\ v1.0
        """)
        print(f"{UI.RESET}{UI.BOLD}   P2P Auction UIent System{UI.RESET}")
        print(f"{UI.GREY}   ─────────────────────────{UI.RESET}\n")
        print(f"{UI.GREEN}[+] Initializing System Sequence...{UI.RESET}")

    @staticmethod
    def step(message, status="OK", color=GREEN):
        print(f" ├── {message:<40} [{color}{status}{UI.RESET}]")
        time.sleep(0.05)

    def sys_ready():
        print(f"\n{UI.BOLD}>>> System Ready. Entering Command Mode...{UI.RESET}\n")


    @staticmethod
    def sub_step(key, value):
        print(f" │   └── {UI.GREY}{key}: {UI.RESET}{value}")

    @staticmethod
    def end_step(message, status="DONE"):
        print(f" └── {message:<40} [{UI.GREEN}{status}{UI.RESET}]")

    @staticmethod
    def setup_error(message):
        print(f" └── {UI.RED}ERROR: {message}{UI.RESET}")

    @staticmethod
    def help():
        CMD = UI.BOLD + UI.CYAN
        ARG = UI.RESET + UI.GREY
        print(f"\n{UI.BOLD}   COMMAND SYNTAX{UI.RESET}")
        print(f"{UI.GREY}   ──────────────{UI.RESET}")
        print(f"   {CMD}/bid      {ARG}{{auction_id}} {{amount}}{UI.RESET}")
        print(f"   {CMD}/auction  {ARG}{{item_name}} {{min_bid}}{UI.RESET}")
        print(f"   {CMD}/status   {ARG}(Check wallet & auctions){UI.RESET}")
        print(f"   {CMD}/exit     {ARG}(Close UIent){UI.RESET}")
        print()

    # =========================================================
    #  PART 2: MAIN LOGS (The Headers)
    # =========================================================

    @staticmethod
    def _timestamp():
        if not UI.SHOW_TIME: return ""
        now = datetime.now().strftime("%H:%M:%S")
        return f"{UI.GREY}[{now}]{UI.RESET} "

    @staticmethod
    def _log(tag, color, message):
        """Prints the main header line: [TIME] [TAG] Message"""
        ts = UI._timestamp()
        print(f"{ts}{UI.BOLD}{color}[{tag}]{UI.RESET} {message}")

    @staticmethod
    def peer(msg):
        UI._log("PEER", UI.GREEN, msg)

    @staticmethod
    def security(msg):
        UI._log("SECURITY", UI.BLUE, msg)

    @staticmethod
    def success(msg):
        UI._log("SUCCESS", UI.GREEN, msg)

    @staticmethod
    def error(msg):
        UI._log("ERROR", UI.RED, msg)

    @staticmethod
    def warn(msg):
        UI._log("WARN", UI.MAGENTA, msg)

    @staticmethod
    def info(msg):
        UI._log("INFO", UI.GREY, msg)

    @staticmethod
    def auction(msg):
        UI._log("AUCTION", UI.YELLOW, msg)

    @staticmethod
    def sys(msg):
        UI._log("SYSTEM", UI.CYAN, msg)

    # =========================================================
    #  PART 3: SUB LOGS (The Details)
    # =========================================================

    @staticmethod
    def _sub(color, message):
        """Prints an indented branch: [TIME]    └── Message"""
        ts = UI._timestamp()
        # The └── symbol takes the color of the context
        print(f"{ts}   {color}└──{UI.RESET} {message}")

    @staticmethod
    def sub_peer(msg):
        UI._sub(UI.GREEN, msg)

    @staticmethod
    def sub_security(msg):
        UI._sub(UI.BLUE, msg)

    @staticmethod
    def sub_error(msg):
        UI._sub(UI.RED, msg)

    @staticmethod
    def sub_warn(msg):
        UI._sub(UI.MAGENTA, msg)

    @staticmethod
    def sub_info(msg):
        UI._sub(UI.GREY, msg)

    @staticmethod
    def sub_auction(msg):
        UI._sub(UI.YELLOW, msg)

    @staticmethod
    def sub_sys(msg):
        UI._sub(UI.CYAN, msg)