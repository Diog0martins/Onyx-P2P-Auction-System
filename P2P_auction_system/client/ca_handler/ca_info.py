from local_test import TEST

if TEST == 1:
    CA_IP = "127.0.0.1"
else:
    #CA_IP = "192.168.89.52"
    CA_IP = "172.26.165.74"


CA_PORT = 8443
CA_URL = f"http://{CA_IP}:{CA_PORT}"