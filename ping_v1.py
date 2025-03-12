#!/usr/bin/env python

import argparse
import time
import jcs
from jnpr.junos import Device
from junos import Junos_Context

# ------------------ Configuración Global ------------------
RPC_TIMEOUT = 90  # Timeout global en segundos

# ------------------ Argumentos CLI ------------------
parser = argparse.ArgumentParser(description="Script para hacer ping con RTT en Juniper (on-box)")
parser.add_argument("--count", type=int, required=True, help="Número de paquetes de ping por host")
args = parser.parse_args()

COUNT = args.count

# ------------------ Lista de Hosts ------------------
HOSTS_LIST = [
    "201.154.139.1"
]

# ------------------ Función de logging ------------------
def log_syslog(message, level="info"):
    level_map = {
        "info": "external.info",
        "warn": "external.warn",
        "error": "external.crit"
    }
    jcs.syslog(level_map.get(level, "external.info"), message)

# ------------------ Función para hacer ping ------------------
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
    log_syslog("🔍 Iniciando pruebas de conectividad (on-box)...", level="info")
    output_messages = []
    start_time = time.time()

    try:
        dev = Device(timeout=RPC_TIMEOUT)
        dev.open()
        log_syslog("✅ Conexión abierta con el dispositivo Juniper", level="info")
        log_syslog(f"⏱ Timeout RPC configurado: {dev.timeout} segundos", level="info")

        for host in HOSTS_LIST:
            log_syslog(f"➡ Procesando host: {host}", level="info")
            msg = ping_host(dev, host, COUNT)
            output_messages.append(msg)

        dev.close()
        log_syslog("✅ Conexión cerrada con el dispositivo", level="info")

        end_time = time.time()
        time_duration = round(end_time - start_time, 2)
        log_syslog(f"🕓 Tiempo total de ejecución del script: {time_duration} segundos", level="info")

    except Exception as e:
        log_syslog(f"[ERROR] No se pudo conectar con el dispositivo: {str(e)}", level="error")

# ------------------ Punto de entrada ------------------
if __name__ == "__main__":
    main()
