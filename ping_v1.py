import jcs
import time
import argparse
from jnpr.junos import Device
from junos import Junos_Context

# Configuración de argumentos
parser = argparse.ArgumentParser(description="Script para realizar pings a hosts desde dispositivo Juniper.")
parser.add_argument("--count", type=int, default=1, help="Número de pings por host.")
parser.add_argument("--host", type=str, default="201.154.139.1", help="Dirección IP o nombre del host a pinguear.")
args = parser.parse_args()

# Variables globales
COUNT = args.count
HOST = args.host

# Funciones de log
def log_info(message):
    jcs.syslog("external.info", f"[INFO] {message}")

def log_warn(message):
    jcs.syslog("external.warn", f"[WARNING] {message}")

def log_error(message):
    jcs.syslog("external.crit", f"[ERROR] {message}")

# Función principal para realizar ping
def ping_host(dev, host):
    """Ejecuta ping hacia un host desde el dispositivo."""
    log_info(f"Iniciando ping a {host} con {COUNT} paquetes...")

    try:
        result = dev.rpc.ping(host=host, count=str(COUNT))

        target_host = result.findtext("target-host", host).strip()
        rtt_min = result.findtext("probe-results-summary/rtt-minimum", "N/A").strip()
        rtt_max = result.findtext("probe-results-summary/rtt-maximum", "N/A").strip()
        rtt_avg = result.findtext("probe-results-summary/rtt-average", "N/A").strip()
        timestamp = str(Junos_Context.get("localtime", "N/A"))

        message = (
            f"RTT details for host {target_host} at time {timestamp} | "
            f"Minimum = {rtt_min} ms | Maximum = {rtt_max} ms | Average = {rtt_avg} ms"
        )

        log_info(message)

    except Exception as e:
        error_msg = f"Ping failed to {host} at time {Junos_Context.get('localtime', 'N/A')}. Error: {str(e)}"
        log_error(error_msg)

# Ejecutar proceso completo
def run_ping_test():
    log_info("Conectando al dispositivo Juniper...")
    start_time = time.time()

    try:
        with Device() as dev:
            log_info("Conexión establecida con éxito.")
            ping_host(dev, HOST)
            log_info("Prueba de conectividad finalizada.")
    except Exception as e:
        log_error(f"No se pudo conectar con el dispositivo: {str(e)}")

    total_time = round(time.time() - start_time, 2)
    log_info(f"Tiempo total de ejecución: {total_time} segundos.")

# Main
def main():
    run_ping_test()

if __name__ == "__main__":
    main()
