
import argparse
import time
import os
import jcs
from jnpr.junos import Device
from junos import Junos_Context
from concurrent.futures import ThreadPoolExecutor, as_completed

# ------------------ Configuración global ------------------
RPC_TIMEOUT = 90  # Timeout en segundos para los RPC
DEFAULT_MAX_WORKERS = os.cpu_count() * 4  # Optimizado para I/O-bound

# ------------------ Argumentos CLI ------------------
parser = argparse.ArgumentParser(description="Script para hacer ping con RTT en Junos (on-box)")
parser.add_argument("--count", type=int, required=True, help="Número de paquetes de ping por host")
parser.add_argument("--threads", type=int, default=DEFAULT_MAX_WORKERS,
                    help=f"Número de hilos para ejecución paralela (por defecto: {DEFAULT_MAX_WORKERS})")
args = parser.parse_args()

COUNT = args.count
MAX_WORKERS = args.threads

# ------------------ Lista de hosts ------------------
HOSTS_LIST = [
    "31.13.89.19",
    "157.240.25.1",
    "157.240.25.62",
    "31.13.89.52",
    "157.240.19.19"
]

# ------------------ Función de logging ------------------
def log_syslog(message, level="info"):
    level_map = {
        "info": "external.warn",
        "warn": "external.warn",
        "error": "external.crit"
    }
    jcs.syslog(level_map.get(level, "external.info"), message)

# ------------------ Función para ejecutar ping ------------------
def ping_host(dev_params):
    dev, host, count = dev_params
    try:
        result = dev.rpc.ping(host=host, count=str(count))

        target_host = result.findtext("target-host", host).strip()
        rtt_min = result.findtext("probe-results-summary/rtt-minimum", "N/A").strip()
        rtt_max = result.findtext("probe-results-summary/rtt-maximum", "N/A").strip()
        rtt_avg = result.findtext("probe-results-summary/rtt-average", "N/A").strip()

        message = (
            f"Ping a {target_host} | Hora: {Junos_Context.get('localtime', 'N/A')} | "
            f"Min: {rtt_min} ms | Max: {rtt_max} ms | Prom: {rtt_avg} ms"
        )
        log_syslog(message, level="info")
        return message

    except Exception as e:
        message = (
            f"Error en ping a {host} | Hora: {Junos_Context.get('localtime', 'N/A')} | "
            f"Detalle: {str(e)}"
        )
        log_syslog(message, level="error")
        return message

# ------------------ Función principal ------------------
def main():
    log_syslog("Iniciando pruebas de conectividad", level="info")
    output_messages = []
    start_time = time.time()

    try:
        dev = Device(timeout=RPC_TIMEOUT)
        dev.open()
        log_syslog("Conexión abierta con el dispositivo", level="info")
        log_syslog(f"Timeout RPC configurado: {dev.timeout} segundos", level="info")
        log_syslog(f"Máximo de hilos: {MAX_WORKERS}", level="info")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(ping_host, (dev, host, COUNT)): host for host in HOSTS_LIST
            }

            for future in as_completed(futures):
                msg = future.result()
                output_messages.append(msg)

        dev.close()
        log_syslog("Conexión cerrada con el dispositivo", level="info")

        end_time = time.time()
        time_duration = round(end_time - start_time, 2)
        log_syslog(f"Tiempo total de ejecución del script: {time_duration} segundos", level="info")

    except Exception as e:
        log_syslog(f"Error al conectar con el dispositivo: {str(e)}", level="error")

# ------------------ Entrada principal ------------------
if __name__ == "__main__":
    main()
