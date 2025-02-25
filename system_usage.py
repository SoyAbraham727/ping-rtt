def log_system_usage():
    """Registra el uso de CPU, memoria y disco en syslog y devuelve los valores corregidos."""
    cpu_percent = round(psutil.cpu_percent(interval=1), 2)
    mem = psutil.virtual_memory()
    disk = round(psutil.disk_usage('/').percent, 2)

    # Cálculo correcto de la memoria usada en porcentaje
    mem_used_percent = round((mem.used / mem.total) * 100, 2) if mem.total > 0 else 0.00

    # Mensaje para syslog
    message = f"CPU: {cpu_percent}%, Memoria: {mem_used_percent}%, Disco: {disk}%"
    jcs.syslog("external.error", f"Uso del sistema - {message}")

    return cpu_percent, mem_used_percent, disk

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
