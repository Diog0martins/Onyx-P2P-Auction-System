import time

class UI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    GREY = "\033[90m"

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
        print(f"{UI.RESET}{UI.BOLD}   P2P Auction Client System{UI.RESET}")
        print(f"{UI.GREY}   -------------------------{UI.RESET}\n")
        print(f"{UI.GREEN}[+] Initializing System Sequence...{UI.RESET}")

    @staticmethod
    def step(message, status="OK", color=GREEN):
        """Prints a tree branch item"""
        print(f" ├── {message:<40} [{color}{status}{UI.RESET}]")
        time.sleep(0.1)

    @staticmethod
    def sub_info(key, value):
        """Prints detailed info under a step (vertical line)"""
        print(f" │   └── {UI.GREY}{key}: {UI.RESET}{value}")

    @staticmethod
    def end_step(message, status="DONE"):
        """Prints the final leaf of the tree"""
        print(f" └── {message:<40} [{UI.GREEN}{status}{UI.RESET}]")
        print(f"\n{UI.BOLD}>>> System Ready. Entering Command Mode...{UI.RESET}\n")

    @staticmethod
    def error(message):
        print(f" └── {UI.RED}ERROR: {message}{UI.RESET}")