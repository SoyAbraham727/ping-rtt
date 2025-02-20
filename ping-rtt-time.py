import jcs
import time
from jnpr.junos import Device
from junos import Junos_Context

# Constantes
HOSTS_LIST = ["204.124.107.83"]
COUNT = 1000

def ping_host(dev, host):
    """Realiza un ping a un host y registra los resultados."""
    try:
        result = dev.rpc.ping(host=host, count=str(COUNT))  # Conversión a str
        rtt_min = result.findtext("probe-results-summary/rtt-minimum", "N/A").strip()
        rtt_max = result.findtext("probe-results-summary/rtt-maximum", "N/A").strip()
        rtt_avg = result.findtext("probe-results-summary/rtt-average", "N/A").strip()
        target_host = result.findtext("target-host", host).strip()
        
        message = (
            f"RTT details for {target_host} at {Junos_Context['localtime']} | "
            f"Min: {rtt_min} ms, Max: {rtt_max} ms, Avg: {rtt_avg} ms"
        )
    except Exception as e:
        message = f"Ping to {host} failed at {Junos_Context['localtime']}. Error: {e}"

    jcs.syslog("external.crit", message)

def main():
    """Establece conexión con el dispositivo, ejecuta pings y mide el tiempo total de ejecución."""
    start_time = time.time()  # Marca de tiempo inicial

    try:
        with Device() as dev:
            for host in HOSTS_LIST:
                ping_host(dev, host)
    
    except Exception as e:
        jcs.syslog("external.error", f"Error al conectar con el dispositivo: {e}")

    end_time = time.time()  # Marca de tiempo final
    execution_time = end_time - start_time  # Cálculo del tiempo total

    # Mensaje de syslog en nivel emerg con el tiempo total de ejecución
    jcs.syslog("external.emerg", f"Ejecución completada en {execution_time:.2f} segundos.")

if __name__ == "__main__":
    main()
