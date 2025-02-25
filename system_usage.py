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

    # Guardar estado inicial en el CSV
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Estado Inicial", initial_cpu, initial_mem, initial_mem_used_mb, initial_mem_free_mb, initial_disk, initial_disk_free_gb, time.strftime("%Y-%m-%d %H:%M:%S")])
