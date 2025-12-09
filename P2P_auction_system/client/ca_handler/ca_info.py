from local_test import TEST

if TEST == 1:
    CA_IP = "127.0.0.1"
else:
    CA_IP = ""


CA_PORT = 8443
CA_URL = f"http://{CA_IP}:{CA_PORT}"