import socket

def get_ip():
    """
        Determines the local machine's primary LAN IP address by
        attempting a dummy connection to a public DNS (does not actually send data).
        Falls back to 127.0.0.1 if no network is available.
    """

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
        print(IP)
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()

    print(f"Local IP: {IP}")
    return IP

