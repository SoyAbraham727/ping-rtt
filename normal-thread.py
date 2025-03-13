import argparse
import time
import os
import jcs
from jnpr.junos import Device
from junos import Junos_Context
from concurrent.futures import ThreadPoolExecutor, as_completed
from jnpr.junos.exception import RpcTimeoutError

# ------------------ Configuracion global ------------------
RPC_TIMEOUT = 90  # Timeout para RPC en segundos

# ------------------ Argumentos CLI ------------------
parser = argparse.ArgumentParser(description="Script para hacer ping con RTT en Junos (on-box)")
parser.add_argument("--count", type=int, required=True, help="Numero de paquetes de ping por host")
args = parser.parse_args()
COUNT = args.count

# ------------------ Lista de hosts ------------------
HOSTS_LIST = [
    "201.154.139.1"
]*5

# ------------------ Numero de hilos ------------------
MAX_WORKERS = len(HOSTS_LIST)

# ------------------ Funcion de log ------------------
def log_syslog(message, thread_id=None, level="info"):
    level_map = {
        "info": "external.warn",
        "warn": "external.warn",
        "error": "external.crit"
    }
    prefix = f"HILO-{thread_id}" if thread_id else "GENERAL"
    full_message = f"{prefix} | {level.upper()} | {message}"
    jcs.syslog(level_map.get(level, "external.warn"), full_message)

# ------------------ Funcion para hacer ping ------------------
def ping_host(dev_params):
    dev, host, count, thread_id = dev_params
    try:
        log_syslog(f"Iniciando ping a {host}", thread_id, level="info")
        result = dev.rpc.ping(host=host, count=str(count))

        target_host = result.findtext("target-host", host).strip()
        rtt_min = result.findtext("probe-results-summary/rtt-minimum", "N/A").strip()
        rtt_max = result.findtext("probe-results-summary/rtt-maximum", "N/A").strip()
        rtt_avg = result.findtext("probe-results-summary/rtt-average", "N/A").strip()

        message = (
            f"Ping a {target_host} | Hora: {Junos_Context.get('localtime', 'N/A')} | "
            f"RTT minimo: {rtt_min} ms | RTT maximo: {rtt_max} ms | RTT promedio: {rtt_avg} ms"
        )
        log_syslog(message, thread_id, level="info")
        return f"{target_host} | RTT min: {rtt_min} ms | max: {rtt_max} ms | prom: {rtt_avg} ms"

    except RpcTimeoutError as e:
        message = (
            f"Timeout en ping a {host} | Hora: {Junos_Context.get('localtime', 'N/A')} | Detalle: {str(e)}"
        )
        log_syslog(message, thread_id, level="error")
        return f"{host} | Timeout"

    except Exception as e:
        message = (
            f"Error en ping a {host} | Hora: {Junos_Context.get('localtime', 'N/A')} | Detalle: {str(e)}"
        )
        log_syslog(message, thread_id, level="error")
        return f"{host} | Error: {str(e)}"

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
                executor.submit(ping_host, (dev, host, COUNT, idx + 1)): host
                for idx, host in enumerate(HOSTS_LIST)
            }

            for i, future in enumerate(as_completed(futures), start=1):
                msg = future.result()
                output_messages.append(f"{i}. {msg}")

        dev.close()
        log_syslog("Conexion cerrada con el dispositivo", level="info")

        end_time = time.time()
        duration = round(end_time - start_time, 2)
        log_syslog(f"Tiempo total de ejecucion: {duration} segundos", level="info")

        print("\nResumen final de resultados:\n")
        for msg in output_messages:
            print(msg)
        print(f"\nTiempo total de ejecucion: {duration} segundos")

    except Exception as e:
        log_syslog(f"Error al conectar con el dispositivo: {str(e)}", level="error")
        print(f"Error al conectar con el dispositivo: {str(e)}")

# ------------------ Entrada principal ------------------
if __name__ == "__main__":
    main()
