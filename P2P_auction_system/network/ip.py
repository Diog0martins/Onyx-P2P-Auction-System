import socket

def get_ip():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    return local_ip