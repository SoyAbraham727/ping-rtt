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

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from jnpr.junos import Device
from jnpr.junos.exception import ConnectError, RpcTimeoutError
from lxml import etree
from datetime import datetime
import syslog

# Parametros de configuracion
HOSTS_LIST = [
    "201.154.139.1",
    "8.8.8.8",
    "1.1.1.1",
    "192.168.1.1",
    "10.10.10.1"
]

COUNT = 5  # Numero de pings por host
MAX_WORKERS = 5  # Numero de hilos
RPC_TIMEOUT = 30  # Timeout RPC en segundos

# Configuracion del log local
logging.basicConfig(filename='ping_test.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def log_syslog(mensaje, level="info"):
    """
    Envia mensaje a syslog y archivo de log local.
    """
    nivel = {
        "info": syslog.LOG_INFO,
        "error": syslog.LOG_ERR,
        "warning": syslog.LOG_WARNING
    }.get(level, syslog.LOG_INFO)

    syslog.syslog(nivel, mensaje)
    logging.info(mensaje)

def ping_host(host, count, thread_id):
    try:
        log_syslog(f"[Hilo-{thread_id}] Iniciando ping a {host}")

        dev = Device(timeout=RPC_TIMEOUT)
        dev.open()
        log_syslog(f"[Hilo-{thread_id}] Conexion establecida con el dispositivo")

        result = dev.rpc.ping(host=host, count=str(count))
        rtt_min = result.findtext("probe-results-summary/rtt-minimum", "N/A").strip()
        rtt_max = result.findtext("probe-results-summary/rtt-maximum", "N/A").strip()
        rtt_avg = result.findtext("probe-results-summary/rtt-average", "N/A").strip()
        hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        mensaje = (f"[Hilo-{thread_id}] Ping a {host} | Hora: {hora} | "
                   f"RTT minimo: {rtt_min} ms | maximo: {rtt_max} ms | promedio: {rtt_avg} ms")
        log_syslog(mensaje)
        dev.close()
        return mensaje

    except RpcTimeoutError as e:
        mensaje = (f"[Hilo-{thread_id}] Timeout en ping a {host} | Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
                   f"| Detalle: RpcTimeoutError(timeout: {RPC_TIMEOUT})")
        log_syslog(mensaje, level="error")
        return mensaje

    except Exception as e:
        mensaje = f"[Hilo-{thread_id}] Error al conectar con {host} | Detalle: {str(e)}"
        log_syslog(mensaje, level="error")
        return mensaje

def main():
    log_syslog("Inicio de pruebas de conectividad")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(ping_host, host, COUNT, idx + 1): host
            for idx, host in enumerate(HOSTS_LIST)
        }

        for future in as_completed(futures):
            resultado = future.result()
            print(resultado)

if __name__ == "__main__":
    main()

