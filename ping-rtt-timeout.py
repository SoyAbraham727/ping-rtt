#!/usr/bin/env python

import argparse
import time
import jcs
from jnpr.junos import Device
from junos import Junos_Context
from jnpr.junos.exception import RpcError

# ------------------ Argumentos CLI ------------------
parser = argparse.ArgumentParser(description="Script on-box para ping con RTT en bloques")
parser.add_argument("--count", type=int, required=True, help="Total de paquetes de ping por host")
parser.add_argument("--chunk", type=int, default=10, help="Tamano de bloques por RPC (default 10)")
args = parser.parse_args()

TOTAL_COUNT = args.count
CHUNK_SIZE = args.chunk

# ------------------ Lista de Hosts ------------------
HOSTS_LIST = [
    "201.154.139.1"
]

# ------------------ Funciones de log ------------------
def log_syslog(message, level="info"):
    level_map = {
        "info": "external.info",
        "warn": "external.warn",
        "error": "external.crit"
    }
    jcs.syslog(level_map.get(level, "external.info"), message)

# ------------------ Funcion principal de ping ------------------
def ping_host(dev, host, total_count, chunk_size):
    current_sent = 0
    total_min = []
    total_max = []
    total_avg = []

    while current_sent < total_count:
        try:
            remaining = total_count - current_sent
            count_now = chunk_size if remaining > chunk_size else remaining
            result = dev.rpc.ping(host=host, count=str(count_now))

            target_host = result.findtext("target-host", host).strip()
            rtt_min = result.findtext("probe-results-summary/rtt-minimum", "0").strip()
            rtt_max = result.findtext("probe-results-summary/rtt-maximum", "0").strip()
            rtt_avg = result.findtext("probe-results-summary/rtt-average", "0").strip()

            total_min.append(float(rtt_min))
            total_max.append(float(rtt_max))
            total_avg.append(float(rtt_avg))

            msg = (f"[OK] Ping a {target_host} | Bloque: {count_now} paquetes | "
                   f"Min: {rtt_min} ms | Max: {rtt_max} ms | Prom: {rtt_avg} ms")
            log_syslog(msg, level="info")

            current_sent += count_now
        except RpcError as e:
            error_msg = f"[ERROR] RPC error durante ping a {host}: {str(e)}"
            log_syslog(error_msg, level="error")
            break
        except Exception as e:
            error_msg = f"[ERROR] Excepcion durante ping a {host}: {str(e)}"
            log_syslog(error_msg, level="error")
            break

    # Resultados finales agregados
    if total_min and total_max and total_avg:
        avg_min = round(sum(total_min) / len(total_min), 2)
        avg_max = round(sum(total_max) / len(total_max), 2)
        avg_avg = round(sum(total_avg) / len(total_avg), 2)
        summary_msg = (f"[RESUMEN] Ping total a {host} | Paquetes: {current_sent} | "
                       f"Promedios - Min: {avg_min} ms | Max: {avg_max} ms | Prom: {avg_avg} ms")
        log_syslog(summary_msg, level="info")

# ------------------ Ejecucion general ------------------
def main():
    start_time = time.time()
    log_syslog("Inicio de pruebas de conectividad on-box", level="info")

    try:
        dev = Device()
        dev.timeout = 90  # Esto es por buena practica, pero puede ser ignorado internamente
        dev.open()

        log_syslog("Conexion abierta con el dispositivo", level="info")
        log_syslog(f"Timeout RPC configurado (valor definido): {dev.timeout} segundos", level="info")

        for host in HOSTS_LIST:
            ping_host(dev, host, TOTAL_COUNT, CHUNK_SIZE)

        dev.close()
        log_syslog("Conexion cerrada con el dispositivo", level="info")

        end_time = time.time()
        duration = round(end_time - start_time, 2)
        log_syslog(f"Tiempo total de ejecucion del script: {duration} segundos", level="info")

    except Exception as e:
        log_syslog(f"[ERROR] Error general: {str(e)}", level="error")

# ------------------ Punto de entrada ------------------
if __name__ == "__main__":
    main()
