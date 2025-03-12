import jcs
import time
import argparse
from jnpr.junos import Device
from junos import Junos_Context

# Lista de hosts
HOSTS_LIST = [
    "201.154.139.1"
]

def log_info(message):
    jcs.syslog("external.info", f"[INFO] {message}")

def log_error(message):
    jcs.syslog("external.crit", f"[ERROR] {message}")

def ping_host(dev, host, count):
    """Ejecuta ping hacia un host desde el dispositivo."""
    log_info(f"Iniciando ping a {host} con {count} paquetes")

    try:
        result = dev.rpc.ping(host=host, count=str(count))
        
        rtt_min = result.findtext("probe-results-summary/rtt-minimum", "N/A").strip()
        rtt_max = result.findtext("probe-results-summary/rtt-maximum", "N/A").strip()
        rtt_avg = result.findtext("probe-results-summary/rtt-average", "N/A").strip()
        target_host = result.findtext("target-host", host).strip()

        log_info(
            f"Ping a {target_host} | Hora: {Junos_Context.get('localtime', 'N/A')} | "
            f"Min: {rtt_min} ms | Max: {rtt_max} ms | Prom: {rtt_avg} ms"
        )

    except Exception as e:
        log_error(f"Fallo el ping a {host} | Hora: {Junos_Context.get('localtime', 'N/A')} | Detalle: {str(e)}")

def run_ping_tests(count):
    """Establece conexion con el dispositivo y ejecuta pings."""
    log_info("Conectando con el dispositivo Juniper...")
    start_time = time.time()

    try:
        with Device() as dev:
            log_info("Conexion establecida correctamente")

            for host in HOSTS_LIST:
                log_info(f"Procesando host: {host}")
                ping_host(dev, host, count)

            log_info("Finalizacion de pruebas de conectividad")

    except Exception as e:
        log_error(f"No se pudo conectar con el dispositivo: {str(e)}")

    total_time = round(time.time() - start_time, 2)
    log_info(f"Tiempo total de ejecucion: {total_time} segundos")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Script para ejecutar ping desde dispositivo Juniper")
    parser.add_argument("--count", type=int, default=5, help="Numero de paquetes por ping (default: 5)")
    return parser.parse_args()

def main():
    args = parse_arguments()
    run_ping_tests(args.count)

if __name__ == "__main__":
    main()
