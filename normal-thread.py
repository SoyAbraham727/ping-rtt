import argparse
import time
import os
import jcs
from jnpr.junos import Device
from junos import Junos_Context
from concurrent.futures import ThreadPoolExecutor, as_completed
from jnpr.junos.exception import RpcTimeoutError
import multiprocessing

# ------------------ Configuracion global ------------------
RPC_TIMEOUT = 90  # Timeout para RPC en segundos

# ------------------ Argumentos CLI ------------------
parser = argparse.ArgumentParser(description="Script para hacer ping con RTT en Junos (on-box)")
parser.add_argument("--count", type=int, required=True, help="Numero de paquetes de ping por host")
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

# ------------------ Determinar numero optimo de hilos ------------------

MAX_WORKERS = len(HOSTS_LIST)

# ------------------ Funcion de log ------------------
def log_syslog(message, level="info"):
    level_map = {
        "info": "external.warn",
        "warn": "external.warn",
        "error": "external.crit"
    }
    jcs.syslog(level_map.get(level, "external.info"), message)

# ------------------ Funcion para hacer ping ------------------
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

    except RpcTimeoutError as e:
        message = (
            f"Timeout en ping a {host} | Hora: {Junos_Context.get('localtime', 'N/A')} | "
            f"Detalle: {str(e)}"
        )
        log_syslog(message, level="error")
        return message

    except Exception as e:
        message = (
            f"Error general en ping a {host} | Hora: {Junos_Context.get('localtime', 'N/A')} | "
            f"Detalle: {str(e)}"
        )
        log_syslog(message, level="error")
        return message

# ------------------ Funcion principal ------------------
def main():
    log_syslog("Inicio de pruebas de conectividad", level="info")
    start_time = time.time()
    output_messages = []

    try:
        dev = Device(timeout=RPC_TIMEOUT, gather_facts=True)
        dev.open()
        log_syslog("Conexion establecida con el dispositivo", level="info")
        log_syslog(f"Timeout RPC: {dev.timeout} segundos", level="info")
        log_syslog(f"Numero de hilos paralelos: {MAX_WORKERS}", level="info")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(ping_host, (dev, host, COUNT)): host for host in HOSTS_LIST
            }

            for future in as_completed(futures):
                msg = future.result()
                output_messages.append(msg)

        dev.close()
        log_syslog("Conexion cerrada con el dispositivo", level="info")

        end_time = time.time()
        duration = round(end_time - start_time, 2)
        log_syslog(f"Tiempo total de ejecucion: {duration} segundos", level="info")

    except Exception as e:
        log_syslog(f"Fallo al conectar con el dispositivo: {str(e)}", level="error")

# ------------------ Entrada principal ------------------
if __name__ == "__main__":
    main()
