import jcs
import time
from jnpr.junos import Device
from junos import Junos_Context

# Constantes
HOSTS_LIST = [
    "201.154.139.1"
    ]

COUNT = 5 

def ping_host(dev, host):
    """Realiza un ping a un host y registra los resultados."""
    jcs.syslog("external.error", f"Iniciando ping a {host}")

    try:
        result = dev.rpc.ping(host=host, count=str(COUNT))
        rtt_min = result.findtext("probe-results-summary/rtt-minimum", "N/A").strip()
        rtt_max = result.findtext("probe-results-summary/rtt-maximum", "N/A").strip()
        rtt_avg = result.findtext("probe-results-summary/rtt-average", "N/A").strip()
        target_host = result.findtext("target-host", host).strip()
        
        message = (
            f"RTT para {target_host} a las {Junos_Context['localtime']} | "
            f"Min: {rtt_min} ms, Máx: {rtt_max} ms, Prom: {rtt_avg} ms"
        )
        jcs.syslog("external.error", f"Ping exitoso a {target_host}")
    except Exception as e:
        message = f"Ping a {host} fallo en {Junos_Context['localtime']}. Error: {e}"
        jcs.syslog("external.crit", f"Error en ping a {host}: {e}")
    
    jcs.syslog("external.crit", message)

def main():
    """Establece conexion con el dispositivo y ejecuta pings a los hosts."""
    jcs.syslog("external.error", "Iniciando conexion con el dispositivo Juniper")
    start_time = time.time()

    try:
        with Device() as dev:
            jcs.syslog("external.error", "Conexion establecida con exito")

            for host in HOSTS_LIST:
                jcs.syslog("external.error", f"Procesando host: {host}")
                ping_host(dev, host)
            
            jcs.syslog("external.error", "Finalizacion de pruebas de ping")
    
    except Exception as e:
        jcs.syslog("external.crit", f"Error al conectar con el dispositivo: {e}")
    
    total_time = round(time.time() - start_time, 3)
    jcs.syslog("external.error", f"[FINALIZACION] Ejecucion del script finalizada en {total_time}")

if __name__ == "__main__":
    main()
