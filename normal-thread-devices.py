import argparse
import time
import jcs
from jnpr.junos import Device
from junos import Junos_Context
from concurrent.futures import ThreadPoolExecutor, as_completed

# ------------------ Configuración global ------------------
RPC_TIMEOUT = 90  # Timeout en segundos para los RPC

# ------------------ Argumentos CLI ------------------
parser = argparse.ArgumentParser(description="Script para hacer ping con RTT en Junos (on-box)")
parser.add_argument("--count", type=int, required=True, help="Número de paquetes de ping por host")
args = parser.parse_args()

COUNT = args.count

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

# ------------------ Función para ejecutar ping con conexión propia ------------------
def ping_host_with_connection(host, count):
    try:
        dev = Device(timeout=RPC_TIMEOUT)
        dev.open()
        log_syslog(f"Conexión abierta para host: {host}", level="info")

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

        dev.close()
        log_syslog(f"Conexión cerrada para host: {host}", level="info")

        return message

    except Exception as e:
        error_msg = (
            f"Error en ping a {host} | Hora: {Junos_Context.get('localtime', 'N/A')} | "
            f"Detalle: {str(e)}"
        )
        log_syslog(error_msg, level="error")
        return error_msg

# ------------------ Función principal ------------------
def main():
    log_syslog("Iniciando pruebas de conectividad paralelas (una conexión por host)", level="info")
    output_messages = []
    start_time = time.time()

    try:
        with ThreadPoolExecutor(max_workers=len(HOSTS_LIST)) as executor:
            future_to_host = {executor.submit(ping_host_with_connection, host, COUNT): host for host in HOSTS_LIST}

            for future in as_completed(future_to_host):
                result = future.result()
                output_messages.append(result)

        end_time = time.time()
        duration = round(end_time - start_time, 2)
        log_syslog(f"Tiempo total de ejecución del script: {duration} segundos", level="info")

    except Exception as e:
        log_syslog(f"Error general en ejecución del script: {str(e)}", level="error")

# ------------------ Entrada principal ------------------
if __name__ == "__main__":
    main()
