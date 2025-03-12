#!/usr/bin/env python

import argparse
import jcs
import time
from junos import Junos_Context

parser = argparse.ArgumentParser(description="Script para ping con RTT en Juniper")
parser.add_argument("--count", type=int, required=True, help="Número de paquetes de ping por host")
args = parser.parse_args()

COUNT = args.count

# Lista fija de hosts
HOSTS_LIST = [
    "201.154.139.1"
]

# Funciones de logging
def log_warning(message):
    jcs.syslog("external.warn", f"[WARNING] {message}")

def log_error(message):
    jcs.syslog("external.crit", f"[ERROR] {message}")

def ping_host(host):
    """Realiza ping y muestra RTT detallado."""
    log_warning(f"Iniciando ping a {host} con {COUNT} paquetes")

    try:
        result = jcs.invoke("ping", {"host": host, "count": str(COUNT)})

        target_host = result.findtext("target-host", host).strip()
        rtt_min = result.findtext("probe-results-summary/rtt-minimum", "N/A").strip()
        rtt_max = result.findtext("probe-results-summary/rtt-maximum", "N/A").strip()
        rtt_avg = result.findtext("probe-results-summary/rtt-average", "N/A").strip()

        message = (
            f"Ping a {target_host} | Hora: {Junos_Context.get('localtime', 'N/A')} | "
            f"Min: {rtt_min} ms | Max: {rtt_max} ms | Prom: {rtt_avg} ms"
        )
        log_warning(message)

    except Exception as e:
        log_error(f"Fallo el ping a {host} | Hora: {Junos_Context.get('localtime', 'N/A')} | Detalle: {str(e)}")

def run_ping_tests():
    """Realiza pruebas de conectividad."""
    log_warning("Ejecutando pruebas de conectividad (on-box)...")

    start_time = time.time()
    try:
        for host in HOSTS_LIST:
            ping_host(host)

        log_warning("Finalización de pruebas de conectividad")

    except Exception as e:
        log_error(f"Error general durante pruebas de conectividad: {str(e)}")

    total_time = round(time.time() - start_time, 2)
    log_warning(f"Tiempo total de ejecución: {total_time} segundos")

def main():
    run_ping_tests()

if __name__ == "__main__":
    main()
