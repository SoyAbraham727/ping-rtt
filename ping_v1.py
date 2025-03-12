#!/usr/bin/env python

import argparse
import time
import jcs
from jnpr.junos import Device
from junos import Junos_Context

# ------------------ Argumentos CLI ------------------
parser = argparse.ArgumentParser(description="Script para hacer ping con RTT en Juniper on-box")
parser.add_argument("--count", type=int, required=True, help="Número de paquetes de ping por host")
args = parser.parse_args()

COUNT = args.count

# ------------------ Lista de Hosts ------------------
HOSTS_LIST = [
    "201.154.139.1",
    "8.8.8.8"
]

# ------------------ Funciones de log ------------------
def log_syslog(message, level="info"):
    level_map = {
        "info": "external.info",
        "warn": "external.warn",
        "error": "external.crit"
    }
    jcs.syslog(level_map.get(level, "external.info"), message)

# ------------------ Función principal de ping ------------------
def ping_host(dev, host, count):
    try:
        result = dev.rpc.ping(host=host, count=str(count))

        target_host = result.findtext("target-host", host).strip()
        rtt_min = result.findtext("probe-results-summary/rtt-minimum", "N/A").strip()
        rtt_max = result.findtext("probe-results-summary/rtt-maximum", "N/A").strip()
        rtt_avg = result.findtext("probe-results-summary/rtt-average", "N/A").strip()

        message = (
            f"[OK] Ping a {target_host} | Hora: {Junos_Context.get('localtime', 'N/A')} | "
            f"Min: {rtt_min} ms | Max: {rtt_max} ms | Prom: {rtt_avg} ms"
        )
        log_syslog(message, level="info")
        return message

    except Exception as e:
        message = (
            f"[ERROR] Fallo el ping a {host} | Hora: {Junos_Context.get('localtime', 'N/A')} | "
            f"Detalle: {str(e)}"
        )
        log_syslog(message, level="error")
        return message

# ------------------ Ejecución general ------------------
def main():
    log_syslog("Iniciando pruebas de conectividad (on-box)...", level="info")
    output_messages = []

    try:
        dev = Device()
        dev.open()
        log_syslog("Conexión abierta con el dispositivo Juniper", level="info")

        for host in HOSTS_LIST:
            msg = ping_host(dev, host, COUNT)
            output_messages.append(msg)

        dev.close()
        log_syslog("Conexión cerrada con el dispositivo", level="info")

    except Exception as e:
        log_syslog(f"[ERROR] No se pudo conectar con el dispositivo: {str(e)}", level="error")

    # ------------------ Guardar en archivo ------------------
    try:
        with open("/var/tmp/resultados_ping.txt", "w") as file:
            for line in output_messages:
                file.write(line + "\n")
    except Exception as e:
        log_syslog(f"[ERROR] No se pudo escribir en archivo: {str(e)}", level="error")

# ------------------ Punto de entrada ------------------
if __name__ == "__main__":
    main()
