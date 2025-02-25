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
