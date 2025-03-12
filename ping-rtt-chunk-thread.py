#!/usr/bin/env python

import argparse
import time
import jcs
from jnpr.junos import Device
from concurrent.futures import ThreadPoolExecutor, as_completed

# ------------------ Argumentos CLI ------------------
parser = argparse.ArgumentParser(description="Script para pruebas de ping con RTT en Junos (multihilo)")
parser.add_argument("--count", type=int, required=True, help="Numero total de paquetes por host")
parser.add_argument("--chunk", type=int, default=10, help="Tamano de cada bloque de pings")
args = parser.parse_args()

COUNT = args.count
CHUNK_SIZE = args.chunk

# ------------------ Lista de hosts ------------------
HOSTS_LIST = [
    "201.154.139.1"
]

# ------------------ Funcion de log ------------------
def log_syslog(msg, level="info"):
    levels = {
        "info": "external.info",
        "warn": "external.warn",
        "error": "external.crit"
    }
    jcs.syslog(levels.get(level, "external.info"), msg)

# ------------------ Funcion de ejecucion de ping ------------------
def ejecutar_ping(dev_timeout, host, chunk_id, start_pkt, count):
    try:
        dev = Device()
        dev.timeout = dev_timeout
        dev.open()

        result = dev.rpc.ping(host=host, count=str(count))

        rtt_min = float(result.findtext("probe-results-summary/rtt-minimum", "0").strip())
        rtt_max = float(result.findtext("probe-results-summary/rtt-maximum", "0").strip())
        rtt_avg = float(result.findtext("probe-results-summary/rtt-average", "0").strip())

        dev.close()

        log_syslog(
            f"OK - Chunk {chunk_id} ({start_pkt + 1}-{start_pkt + count}) ping a {host} | Min: {rtt_min} ms | Max: {rtt_max} ms | Prom: {rtt_avg} ms"
        )

        return {"min": rtt_min, "max": rtt_max, "avg": rtt_avg}

    except Exception as e:
        log_syslog(
            f"ERROR - Chunk {chunk_id} ({start_pkt + 1}-{start_pkt + count}) fallo ping a {host} | Detalle: {str(e)}",
            level="error"
        )
        return {"min": 0.0, "max": 0.0, "avg": 0.0}

# ------------------ Funcion de resumen RTT ------------------
def calcular_resumen(mins, maxs, avgs):
    if not mins or not maxs or not avgs:
        return "0", "0", "0"
    return str(min(mins)), str(max(maxs)), str(round(sum(avgs) / len(avgs), 2))

# ------------------ Funcion principal ------------------
def main():
    log_syslog("Inicio de prueba de conectividad con ping multihilo")
    inicio = time.time()

    try:
        dev = Device()
        dev.timeout = 120
        dev.open()
        log_syslog("Conexion con el dispositivo exitosa")
        dev.close()

        for host in HOSTS_LIST:
            total_chunks = (COUNT + CHUNK_SIZE - 1) // CHUNK_SIZE
            log_syslog(f"Iniciando ping a {host} con {COUNT} paquetes en {total_chunks} bloques")

            resultados_min = []
            resultados_max = []
            resultados_avg = []

            dev_timeout = 120

            with ThreadPoolExecutor(max_workers=total_chunks) as executor:
                futures = []

                for i in range(total_chunks):
                    inicio_chunk = i * CHUNK_SIZE
                    cantidad = min(CHUNK_SIZE, COUNT - inicio_chunk)
                    futures.append(
                        executor.submit(
                            ejecutar_ping,
                            dev_timeout,
                            host,
                            i + 1,
                            inicio_chunk,
                            cantidad
                        )
                    )

                for future in as_completed(futures):
                    r = future.result()
                    resultados_min.append(r["min"])
                    resultados_max.append(r["max"])
                    resultados_avg.append(r["avg"])

            final_min, final_max, final_avg = calcular_resumen(resultados_min, resultados_max, resultados_avg)

            log_syslog(
                f"RESUMEN - Host: {host} | Minimo: {final_min} ms | Maximo: {final_max} ms | Promedio: {final_avg} ms"
            )

        fin = time.time()
        log_syslog(f"Tiempo total de ejecucion: {round(fin - inicio, 2)} segundos")

    except Exception as e:
        log_syslog(f"ERROR - No se pudo conectar al dispositivo: {str(e)}", level="error")

# ------------------ Ejecucion ------------------
if __name__ == "__main__":
    main()
