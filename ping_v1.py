import jcs
import psutil
from jnpr.junos import Device
from junos import Junos_Context

# Constantes
HOSTS_LIST = [
    "31.13.89.19",
    "157.240.25.",
    "157.240.25.",
    "31.13.89.52",
    "157.240.19."
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
            f"Mín: {rtt_min} ms, Máx: {rtt_max} ms, Prom: {rtt_avg} ms"
        )
        jcs.syslog("external.error", f"Ping exitoso a {target_host}")
    except Exception as e:
        message = f"Ping a {host} falló en {Junos_Context['localtime']}. Error: {e}"
        jcs.syslog("external.crit", f"Error en ping a {host}: {e}")
    
    jcs.syslog("external.crit", message)

def main():
    """Establece conexión con el dispositivo y ejecuta pings a los hosts."""
    jcs.syslog("external.error", "Iniciando conexión con el dispositivo Juniper")

    try:
        with Device() as dev:
            jcs.syslog("external.error", "Conexión establecida con éxito")

            for host in HOSTS_LIST:
                jcs.syslog("external.error", f"Procesando host: {host}")
                ping_host(dev, host)
            
            jcs.syslog("external.error", "Finalización de pruebas de ping")
    
    except Exception as e:
        jcs.syslog("external.crit", f"Error al conectar con el dispositivo: {e}")
    
    jcs.syslog("external.error", "Ejecución del script finalizada")

if __name__ == "__main__":
    main()
