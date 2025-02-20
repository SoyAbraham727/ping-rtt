import jcs
from jnpr.junos import Device
from junos import Junos_Context

# Constantes
HOSTS_LIST = ["204.124.107.83", "204.124.107.82", "1.1.1.1"]
COUNT = 5 

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
    """Establece conexión con el dispositivo y ejecuta pings a los hosts."""
    try:
        with Device() as dev:
            for host in HOSTS_LIST:
                ping_host(dev, host)
    
    except Exception as e:
        jcs.syslog("external.error", f"Error al conectar con el dispositivo: {e}")

if __name__ == "__main__":
    main()
