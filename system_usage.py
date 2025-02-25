import jcs
import psutil
import csv
import time
import os
from jnpr.junos import Device
from junos import Junos_Context

# Lista de hosts (ejemplo)
HOSTS_LIST = [
    "204.124.107.82"
]
COUNT = 1  # Número de pings por host

# Nombre del archivo CSV donde se guardarán los resultados
csv_filename = "/var/db/scripts/op/ping_results.csv"

# Si el archivo no existe, crear con los encabezados
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Host", "CPU (%)", "Memoria (%)", "Memoria Usada (MB)", "Memoria Libre (MB)", "Disco (%)", "Disco Libre (GB)", "RTT Min (ms)", "RTT Max (ms)", "RTT Prom (ms)", "Hora"])

def log_system_usage():
    """Registra el uso de CPU, memoria y disco en syslog y devuelve los valores corregidos."""
    cpu_percent = round(psutil.cpu_percent(interval=1), 2)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Cálculo de la memoria usada y libre en MB
    mem_used_percent = round((mem.used / mem.total) * 100, 2) if mem.total > 0 else 0.00
    mem_used_mb = round(mem.used / (1024 * 1024), 2)
    mem_free_mb = round(mem.free / (1024 * 1024), 2)

    # Cálculo del espacio libre en disco en GB
    disk_percent = round(disk.percent, 2)
    disk_free_gb = round(disk.free / (1024 * 1024 * 1024), 2)

    # Mensaje para syslog
    message = f"CPU: {cpu_percent}%, Memoria: {mem_used_percent}% ({mem_used_mb} MB usados, {mem_free_mb} MB libres), Disco: {disk_percent}% ({disk_free_gb} GB libres)"
    jcs.syslog("external.error", f"Uso del sistema - {message}")

    return cpu_percent, mem_used_percent, mem_used_mb, mem_free_mb, disk_percent, disk_free_gb

def ping_host(host):
    """Realiza un ping a un host con su propia conexión y guarda los resultados en el CSV."""
    jcs.syslog("external.error", f"Iniciando ping a {host}")
    cpu_percent, mem_percent, mem_used_mb, mem_free_mb, disk_percent, disk_free_gb = log_system_usage()  # Registrar métricas antes del ping

    try:
        with Device() as dev:  # Cada host maneja su propia conexión
            result = dev.rpc.ping(host=host, count=str(COUNT))
            rtt_min = round(float(result.findtext("probe-results-summary/rtt-minimum", "0.0")), 2)
            rtt_max = round(float(result.findtext("probe-results-summary/rtt-maximum", "0.0")), 2)
            rtt_avg = round(float(result.findtext("probe-results-summary/rtt-average", "0.0")), 2)
            target_host = result.findtext("target-host", host).strip()
            
            message = (
                f"RTT para {target_host} a las {Junos_Context['localtime']} | "
                f"Mín: {rtt_min} ms, Máx: {rtt_max} ms, Prom: {rtt_avg} ms"
            )
            jcs.syslog("external.error", f"Ping exitoso a {target_host}")

    except Exception as e:
        message = f"Ping a {host} falló en {Junos_Context['localtime']}. Error: {e}"
        jcs.syslog("external.crit", f"Error en ping a {host}: {e}")
        rtt_min, rtt_max, rtt_avg = 0.00, 0.00, 0.00  # En caso de fallo, valores numéricos con 2 decimales

    jcs.syslog("external.crit", message)

    # Guardar resultados en CSV (modo 'a' para agregar sin sobrescribir)
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            host,
            f"{cpu_percent:.2f}",
            f"{mem_percent:.2f}",
            f"{mem_used_mb:.2f}",
            f"{mem_free_mb:.2f}",
            f"{disk_percent:.2f}",
            f"{disk_free_gb:.2f}",
            f"{rtt_min:.2f}",
            f"{rtt_max:.2f}",
            f"{rtt_avg:.2f}",
            time.strftime("%Y-%m-%d %H:%M:%S")
        ])

def main():
    """Ejecuta el proceso para cada host y guarda los resultados en CSV."""
    jcs.syslog("external.error", "Iniciando conexión con el dispositivo Juniper")
    log_system_usage()  # Monitorear uso antes de conectar

    for host in HOSTS_LIST:
        jcs.syslog("external.error", f"Procesando host: {host}")
        ping_host(host)  # Ahora cada ping maneja su propia conexión
    
    jcs.syslog("external.error", "Ejecución del script finalizada")
    log_system_usage()  # Monitorear uso al finalizar

if __name__ == "__main__":
    main()
