import jcs
import psutil
from jnpr.junos import Device
from junos import Junos_Context

# Constantes
HOSTS_LIST = ["204.124.107.83", "204.124.107.82", "1.1.1.1"]
COUNT = 5 

def log_system_usage():
    """Registra el uso de CPU, memoria y disco en syslog (nivel ERROR)."""
    cpu_percent = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    jcs.syslog("external.error", 
        f"Uso del sistema - CPU: {cpu_percent}%, Memoria: {mem.percent}%, Disco: {disk.percent}%"
    )

def ping_host(dev, host):
    """Realiza un ping a un host y registra los resultados."""
    jcs.syslog("external.error", f"Iniciando ping a {host}")
    log_system_usage()  # Registrar métricas antes del ping

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
    log_system_usage()  # Registrar métricas después del ping

def main():
    """Establece conexión con el dispositivo y ejecuta pings a los hosts."""
    jcs.syslog("external.error", "Iniciando conexión con el dispositivo Juniper")
    log_system_usage()  # Monitorear uso antes de conectar

    try:
        with Device() as dev:
            jcs.syslog("external.error", "Conexión establecida con éxito")
            log_system_usage()

            for host in HOSTS_LIST:
                jcs.syslog("external.error", f"Procesando host: {host}")
                ping_host(dev, host)
            
            jcs.syslog("external.error", "Finalización de pruebas de ping")
    
    except Exception as e:
        jcs.syslog("external.crit", f"Error al conectar con el dispositivo: {e}")
    
    jcs.syslog("external.error", "Ejecución del script finalizada")
    log_system_usage()  # Monitorear uso al finalizar

if __name__ == "__main__":
    main()
