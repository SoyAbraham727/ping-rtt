import jcs
from jnpr.junos import Device
from junos import Junos_Context

# Constantes
HOSTS_LIST = ["192.168.1.1", "8.8.8.8", "1.1.1.1"]
COUNT = 5

def ping_host(dev, host):
    """Realiza un ping a un host y registra los resultados en syslog."""
    try:
        result = dev.rpc.ping(host=host, count=COUNT)
        rtt_min = result.findtext("probe-results-summary/rtt-minimum", "N/A").strip()
        rtt_max = result.findtext("probe-results-summary/rtt-maximum", "N/A").strip()
        rtt_avg = result.findtext("probe-results-summary/rtt-average", "N/A").strip()
        target_host = result.findtext("target-host", host).strip()

        message = (
            f"[PING] {target_host} | {Junos_Context['localtime']} | "
            f"Min: {rtt_min} ms, Max: {rtt_max} ms, Avg: {rtt_avg} ms"
        )
    except Exception as e:
        message = f"[ERROR] Ping a {host} fallido | {Junos_Context['localtime']} | Error: {e}"

    jcs.syslog("external.crit", message)

def main():
    """Establece conexión con el dispositivo y ejecuta pings a los hosts."""
    try:
        with Device() as dev:
            for host in HOSTS_LIST:
                ping_host(dev, host)
    except Exception as e:
        jcs.syslog("external.error", f"[ERROR] No se pudo conectar con el dispositivo | Error: {e}")

if __name__ == "__main__":
    main()
