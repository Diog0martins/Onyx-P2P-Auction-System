import json
import time
import os
from datetime import datetime

# Thresholds for triggering security alerts
MAX_RPM = 60  # Alert if requests per minute exceed 60
MAX_LATENCY_MS = 1.2  # Alert if RSA processing latency exceeds 200ms
LOG_FILE = 'ca_security.log'

# ANSI color codes for terminal output
CLR_RESET = "\033[0m"
CLR_RED = "\033[91m"
CLR_GREEN = "\033[92m"
CLR_YELLOW = "\033[93m"
CLR_BLUE = "\033[94m"
CLR_BOLD = "\033[1m"


def run_dashboard():
    """
    Main loop that monitors the CA security log in real time.
    It parses JSON entries and evaluates system health against predefined thresholds.
    """
    print(f"{CLR_BOLD}{CLR_BLUE}[SYSTEM] CA Security Monitor Started{CLR_RESET}")
    print(f"{CLR_BLUE}[INFO] Monitoring file: {LOG_FILE}{CLR_RESET}")
    print(f"{CLR_BLUE}[INFO] Thresholds: RPM > {MAX_RPM} | Latency > {MAX_LATENCY_MS}ms{CLR_RESET}\n")

    # Create the log file if it does not exist
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            pass
        print(f"{CLR_YELLOW}[WARN] Log file not found. An empty log file was created: {LOG_FILE}{CLR_RESET}")

    try:
        # Open the log file in read mode
        with open(LOG_FILE, 'r') as f:
            # Move to the end of the file to ignore old logs and start real-time monitoring
            f.seek(0, 2)

            while True:
                line = f.readline()

                # If no new line is found, wait briefly and try again
                if not line:
                    time.sleep(0.1)
                    continue

                try:
                    # Parse the structured JSON log entry
                    log_data = json.loads(line)

                    event = log_data.get("event_type", "unknown")
                    latency = log_data.get("latency_ms", 0)
                    status = log_data.get("status", "unknown")
                    source_ip = log_data.get("source_ip", "0.0.0.0")
                    timestamp = log_data.get("timestamp", "")

                    is_alert = False
                    log_color = CLR_GREEN

                    # Alert if status is 'fail' (potential exploit attempt or system failure)
                    if status == "fail":
                        is_alert = True
                        log_color = CLR_RED

                    # Alert if latency is too high (potential resource exhaustion / CPU DoS)
                    if latency > MAX_LATENCY_MS:
                        is_alert = True
                        log_color = CLR_YELLOW

                    if is_alert:
                        print(f"{CLR_BOLD}{CLR_RED}[SECURITY ALERT]{CLR_RESET} Potential Abuse Detected!")
                        print(f"  |> Reason: {'High Latency' if latency > MAX_LATENCY_MS else 'Failed Operation'}")
                        print(f"  |> Source: {source_ip} | Event: {event}")

                    # Standard log display
                    ts_display = datetime.now().strftime('%H:%M:%S')
                    print(
                        f"{log_color}[LOG] {ts_display} | {event:<25} | Latency: {latency:>7}ms | Status: {status}{CLR_RESET}"
                    )

                except json.JSONDecodeError:
                    # Skip lines that are not valid JSON
                    continue
                except Exception as e:
                    print(f"{CLR_RED}[ERROR] Monitoring error: {e}{CLR_RESET}")

    except KeyboardInterrupt:
        print(f"\n{CLR_BLUE}[SYSTEM] Monitor reaching shutdown...{CLR_RESET}")
    except Exception as e:
        print(f"{CLR_RED}[FATAL] {e}{CLR_RESET}")


if __name__ == "__main__":
    run_dashboard()