import logging
import json
import time
import threading
from collections import defaultdict

class RelayMonitor:
    def __init__(self):
        # Configurar el logger para escribir en JSON
        self.logger = logging.getLogger("RelayMonitor")
        self.logger.setLevel(logging.INFO)
        fh = logging.FileHandler("relay_security.log")
        self.logger.addHandler(fh)

        # Variables de estado para métricas
        self.lock = threading.Lock()
        self.msg_count_global = 0
        self.conn_count_global = 0
        self.msg_count_per_peer = defaultdict(int)
        self.conn_attempts_per_ip = defaultdict(int)
        self.active_uuids = set()

        # Iniciar hilo en segundo plano para reportar métricas cada minuto
        self.running = True
        self.reporter_thread = threading.Thread(target=self._report_metrics, daemon=True)
        self.reporter_thread.start()

    def _write_log(self, event_type, details):
        """Escribe el log estructurado en JSON."""
        log_entry = {
            "timestamp": time.time(),
            "event": event_type,
            "details": details
        }
        self.logger.info(json.dumps(log_entry))
        print(f"[Monitor Alerta] {event_type} -> {details}") # Imprime en consola para la demo

    def log_connection(self, ip):
        """Llamado cada vez que un socket se conecta al Relay."""
        with self.lock:
            self.conn_count_global += 1
            self.conn_attempts_per_ip[ip] += 1
            
            # REGLA: Si la misma IP se conecta más de 10 veces en un minuto, es un Spike
            if self.conn_attempts_per_ip[ip] > 10:
                self._write_log("connection_spike", {"ip": ip, "attempts": self.conn_attempts_per_ip[ip]})

    def register_uuid(self, uuid, ip):
        """Llamado cuando un peer envía su UUID."""
        with self.lock:
            # REGLA: Si el UUID ya está activo, alguien está haciendo Spoofing o duplicando
            if uuid in self.active_uuids and uuid != "NA":
                self._write_log("uuid_collision", {"uuid": uuid, "ip": ip})
            else:
                self.active_uuids.add(uuid)

    def remove_uuid(self, uuid):
        with self.lock:
            if uuid in self.active_uuids:
                self.active_uuids.remove(uuid)

    def log_message(self, uuid):
        """Llamado cada vez que el Relay retransmite un mensaje."""
        with self.lock:
            self.msg_count_global += 1
            self.msg_count_per_peer[uuid] += 1
            
            # REGLA: Si un solo peer envía más de 20 mensajes por minuto, es Flooding
            if self.msg_count_per_peer[uuid] > 20:
                self._write_log("msg_rate_per_peer", {"uuid": uuid, "rate": self.msg_count_per_peer[uuid]})

    def _report_metrics(self):
        """Se ejecuta cada 60 segundos para guardar las métricas base."""
        while self.running:
            time.sleep(60)
            with self.lock:
                self._write_log("metric_report", {
                    "msgs_per_minute": self.msg_count_global,
                    "connections_per_minute": self.conn_count_global
                })
                # Resetear contadores para el siguiente minuto
                self.msg_count_global = 0
                self.conn_count_global = 0
                self.conn_attempts_per_ip.clear()
                self.msg_count_per_peer.clear()