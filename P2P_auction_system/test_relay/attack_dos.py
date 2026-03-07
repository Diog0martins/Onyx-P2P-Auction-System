import socket
import time
import sys

# Configuração do relay a atacar
RELAY_HOST = '172.26.165.74'
RELAY_PORT = 7000

def attack_connection_flood():
    print(f"\n[+] Iniciando Ataque: Connection Flood (DoS) {RELAY_HOST}:{RELAY_PORT}")
    print("    Abrendo 15 coneções rápidas para disparar a alerta 'connection_spike'...")
    sockets = []
    try:
        for i in range(15):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((RELAY_HOST, RELAY_PORT))
            sockets.append(s)
            print(f"    - Coneção {i+1} estabelecida.")
            time.sleep(0.05) 
    except Exception as e:
        print(f"[-] Erro durante o flood: {e}")
    finally:
        print("[+] Mantendo coneções abertas por 2 segundos...")
        time.sleep(2)
        for s in sockets:
            s.close()
        print("[+] Coneções fechadas.")

def attack_message_spam():
    print(f"\n[+] Iniciando Ataque: Message Spam {RELAY_HOST}:{RELAY_PORT}")
    print("    Enviando 25 mensajes em ráfaga para disparar 'msg_rate_per_peer'...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((RELAY_HOST, RELAY_PORT))
        
        # Registrar un UUID falso
        fake_uuid = "SPAMMER-UUID"
        s.sendall(fake_uuid.encode('utf-8'))
        time.sleep(0.5)

        # Enviar ráfaga de mensajes (flooding)
        for i in range(25):
            spam_msg = f"Mensaje de lixo {i} para congestionar o Relay"
            s.sendall(spam_msg.encode('utf-8'))
            time.sleep(0.02)
            
        print("    - 25 Mensajes enviados com éxito.")
        time.sleep(1) 
        s.close()
    except Exception as e:
        print(f"[-] Erro no spam: {e}")

def attack_uuid_spoofing():
    print(f"\n[+] Iniciando Ataque: UUID Spoofing {RELAY_HOST}:{RELAY_PORT}")
    print("    Tentando conetar 2 sockets simultáneos com o mesmo UUID...")
    target_uuid = "VICTIM-UUID-1234"
    
    try:
        # Coneção 1 (aa víctima legítima)
        s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s1.connect((RELAY_HOST, RELAY_PORT))
        s1.sendall(target_uuid.encode('utf-8'))
        print(f"    - Coneção 1 (legítima) estabelecida com UUID: {target_uuid}")
        time.sleep(1)

        # Conexión 2 (El atacante intentando hacer spoofing del UUID)
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.connect((RELAY_HOST, RELAY_PORT))
        s2.sendall(target_uuid.encode('utf-8'))
        print(f"    - Coneçao 2 (atacante) tentando usar o mesmo UUID: {target_uuid}")
        
        time.sleep(2)
        s1.close()
        s2.close()
        print("[+] Coneções fechadas.")
    except Exception as e:
        print(f"[-] Erro no spoofing: {e}")

def main():
    while True:
        print("\n=== SIMULADOR DE ATAQUES AO RELAY===")
        print("1. Executar Connection Flood (DoS)")
        print("2. Executar Message Spam (Flooding)")
        print("3. Executar UUID Spoofing (Colisión)")
        print("4. Sair")
        
        opcion = input("Escolhe uma opção (1-4): ")
        
        if opcion == '1':
            attack_connection_flood()
        elif opcion == '2':
            attack_message_spam()
        elif opcion == '3':
            attack_uuid_spoofing()
        elif opcion == '4':
            print("Saindo...")
            sys.exit(0)
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    main()