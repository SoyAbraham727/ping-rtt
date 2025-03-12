import jcs
import time
import argparse
from jnpr.junos import Device
from junos import Junos_Context

# Lista de hosts a los que se les hará ping
HOSTS_LIST = [
    "201.154.139.1"
]

def ping_host(dev, host, count):
    """Realiza un ping a un host y registra los resultados."""
    jcs.syslog("external.info", f"[PING] Iniciando ping a {host} con {count} paquetes")

    try:
        result = dev.rpc.ping(host=host, count=str(count))
        rtt_min = result.findtext("probe-results-summary/rtt-minimum", "N/A").strip()
        rtt_max = result.findtext("probe-results-summary/rtt-maximum", "N/A").strip()
        rtt_avg = result.findtext("probe-results-summary/rtt-average", "N/A").strip()
        target_host = result.findtext("target-host", host).strip()
        
        message = (
            f"[PING] Resultado para {target_host} a las {Junos_Context['localtime']} | "
            f"Min: {rtt_min} ms, Máx: {rtt_max} ms, Prom: {rtt_avg} ms"
        )
        jcs.syslog("external.info", message)
    
    except Exception as e:
        error_msg = f"[ERROR] Ping a {host} falló a las {Junos_Context['localtime']}. Detalle: {str(e)}"
        jcs.syslog("external.crit", error_msg)

def main():
    # Parseo de argumentos
    parser = argparse.ArgumentParser(description="Script para hacer ping a hosts desde dispositivo Juniper")
    parser.add_argument("--count", type=int, default=5, help="Número de paquetes a enviar en cada ping (default: 5)")
    args = parser.parse_args()

    count = args.count

    jcs.syslog("external.info", "[INICIO] Estableciendo conexión con el dispositivo Juniper...")
    start_time = time.time()

    try:
        with Device() as dev:
            jcs.syslog("external.info", "[OK] Conexión establecida exitosamente.")

            for host in HOSTS_LIST:
                jcs.syslog("external.info", f"[PROCESO] Ejecutando ping para host: {host}")
                ping_host(dev, host, count)
            
            jcs.syslog("external.info", "[FIN] Pruebas de conectividad finalizadas.")
    
    except Exception as e:
        jcs.syslog("external.crit", f"[ERROR] No se pudo establecer conexión con el dispositivo: {str(e)}")

    total_time = round(time.time() - start_time, 3)
    jcs.syslog("external.info", f"[FINALIZACIÓN] Tiempo total de ejecución: {total_time} segundos.")

if __name__ == "__main__":
    main()
