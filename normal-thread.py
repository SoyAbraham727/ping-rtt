from jnpr.junos import Device
from jnpr.junos.exception import ConnectError, RpcTimeoutError, RpcError
from lxml import etree
import concurrent.futures
import time

# Lista de IPs destino para hacer ping
ips_destino = [
    "157.240.25.1",
    "157.240.25.62",
    "31.13.89.19",
    "31.13.89.52",
    "157.240.19.19"
]

# Configuración
rpc_timeout = 30
numero_hilos = 5
host_dispositivo = "ex4300-V300"  # Puede ser IP o nombre si ya está resuelto en tu entorno

def realizar_ping(ip, dispositivo):
    try:
        print(f"Realizando ping a {ip}...")
        resultado = dispositivo.rpc.ping(host=ip, count="5", timeout=str(rpc_timeout))
        rtt = resultado.xpath(".//probe-results-summary")[0]
        rtt_min = rtt.findtext("rtt-minimum")
        rtt_max = rtt.findtext("rtt-maximum")
        rtt_prom = rtt.findtext("rtt-average")
        print(f"Ping a {ip} | Min: {rtt_min} ms | Max: {rtt_max} ms | Prom: {rtt_prom} ms")
    except RpcTimeoutError:
        print(f"Timeout en ping a {ip} | Detalle: RpcTimeoutError (timeout={rpc_timeout})")
    except RpcError as e:
        print(f"Error general en ping a {ip} | Detalle: {e}")
    except Exception as e:
        print(f"Error inesperado en ping a {ip} | Detalle: {e}")

def main():
    print("Inicio de pruebas de conectividad")
    tiempo_inicio = time.time()

    try:
        with Device(host=host_dispositivo, auto_probe=5) as dev:
            print("Conexión establecida con el dispositivo")
            print(f"Timeout RPC: {rpc_timeout} segundos")
            print(f"Número de hilos paralelos: {numero_hilos}")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=numero_hilos) as executor:
                futures = [executor.submit(realizar_ping, ip, dev) for ip in ips_destino]
                concurrent.futures.wait(futures)

    except ConnectError as e:
        print(f"No se pudo conectar con el dispositivo: {e}")
    except Exception as e:
        print(f"Error general al conectar con el dispositivo: {e}")
    finally:
        tiempo_total = time.time() - tiempo_inicio
        print(f"Tiempo total de ejecución: {tiempo_total:.2f} segundos")

if __name__ == "__main__":
    main()
