#!/usr/bin/env python

import argparse
import time
import jcs
from jnpr.junos import Device
from junos import Junos_Context

# ------------------ Argumentos CLI ------------------
parser = argparse.ArgumentParser(description="Script para hacer ping con RTT en Juniper on-box")
parser.add_argument("--count", type=int, required=True, help="Numero total de paquetes de ping por host")
parser.add_argument("--chunk", type=int, default=10, help="Tamanio de cada bloque de pings")
args = parser.parse_args()

COUNT = args.count
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

# ------------------ Funcion para hacer ping por bloques ------------------
def ping_in_chunks(dev, host, total_count, chunk_size):
    all_min = []
    all_max = []
    all_avg = []

    for i in range(0, total_count, chunk_size):
        current_chunk = min(chunk_size, total_count - i)
        try:
            result = dev.rpc.ping(host=host, count=str(current_chunk))

            rtt_min = result.findtext("probe-results-summary/rtt-minimum", "0").strip()
            rtt_max = result.findtext("probe-results-summary/rtt-maximum", "0").strip()
            rtt_avg = result.findtext("probe-results-summary/rtt-average", "0").strip()

            all_min.append(float(rtt_min))
            all_max.append(float(rtt_max))
            all_avg.append(float(rtt_avg))

            msg = (
                f"[OK] Bloque {i+1}-{i+current_chunk} pings a {host} | "
                f"Min: {rtt_min} ms | Max: {rtt_max} ms | Prom: {rtt_avg} ms"
            )
            log_syslog(msg, level="info")

        except Exception as e:
            error_msg = f"[ERROR] Fallo ping a {host} en bloque {i+1}-{i+current_chunk} | Detalle: {str(e)}"
            log_syslog(error_msg, level="error")

    return all_min, all_max, all_avg

# ------------------ Calculo acumulado ------------------
def calcular_rtt_final(all_min, all_max, all_avg):
    if not all_min or not all_max or not all_avg:
        return "0", "0", "0"
    final_min = str(min(all_min))
    final_max = str(max(all_max))
    final_avg = str(round(sum(all_avg) / len(all_avg), 2))
    return final_min, final_max, final_avg

# ------------------ Ejecucion general ------------------
def main():
    log_syslog("Inicio de pruebas de conectividad on-box", level="info")
    start_time = time.time()

    try:
        dev = Device()
        dev.timeout = 120  # Aumenta timeout RPC si es necesario
        dev.open()
        log_syslog("Conexion abierta con el dispositivo Junos", level="info")
        log_syslog(f"Timeout RPC configurado: {dev.timeout} segundos", level="info")

        for host in HOSTS_LIST:
            log_syslog(f"Iniciando ping a {host} con {COUNT} paquetes en bloques de {CHUNK_SIZE}", level="info")

            all_min, all_max, all_avg = ping_in_chunks(dev, host, COUNT, CHUNK_SIZE)
            final_min, final_max, final_avg = calcular_rtt_final(all_min, all_max, all_avg)

            resumen = (
                f"[RESUMEN] Host: {host} | RTT Minimo: {final_min} ms | "
                f"Maximo: {final_max} ms | Promedio: {final_avg} ms"
            )
            log_syslog(resumen, level="info")

        dev.close()
        end_time = time.time()
        tiempo_total = round(end_time - start_time, 2)
        log_syslog(f"Tiempo total de ejecucion: {tiempo_total} segundos", level="info")

    except Exception as e:
        log_syslog(f"[ERROR] No se pudo conectar con el dispositivo: {str(e)}", level="error")

# ------------------ Punto de entrada ------------------
if __name__ == "__main__":
    main()
