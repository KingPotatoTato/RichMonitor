from flask import Flask, Response, jsonify
import psutil, GPUtil, json, time

app = Flask(__name__)

pc = {
    "cpu": {"percent": 0.0, "freq": 0.0, "maxFreq": 0.0, "temp": 0.0, "cores": 0, "threads": 0},
    "mem": {"total": 0, "available": 0, "used": 0, "percent": 0.0},
    "storage": {},
    "network": {"sent": 0, "recv": 0, "sentPerSec": 0, "recvPerSec": 0},
    "gpu": {"memFree": 0, "memUsed": 0, "percent": 0.0, "temp": 0.0},
    "bootTime": 0,
    "processes": {"cpuTop": {
      "0": {
        "pid": 0,
        "name": "",
        "memPer": 0.0,
        "cpuPer": 0.0
      },
      "1": {
        "pid": 0,
        "name": "",
        "memPer": 0.0,
        "cpuPer": 0.0
      },
      "2": {
        "pid": 0,
        "name": "",
        "memPer": 0.0,
        "cpuPer": 0.0
      },
      "3": {
        "pid": 0,
        "name": "",
        "memPer": 0.0,
        "cpuPer": 0.0
      },
      "4": {
        "pid": 0,
        "name": "",
        "memPer": 0.0,
        "cpuPer": 0.0
      }
    },
    "memTop": {
      "0": {
        "pid": 0,
        "name": "",
        "memPer": 0.0,
        "cpuPer": 0.0
      },
      "1": {
        "pid": 0,
        "name": "",
        "memPer": 0.0,
        "cpuPer": 0.0
      },
      "2": {
        "pid": 0,
        "name": "",
        "memPer": 0.0,
        "cpuPer": 0.0
      },
      "3": {
        "pid": 0,
        "name": "",
        "memPer": 0.0,
        "cpuPer": 0.0
      },
      "4": {
        "pid": 0,
        "name": "",
        "memPer": 0.0,
        "cpuPer": 0.0
      }
    }
  }
}

def getProcessInfo():
    """Get top 5 processes by CPU and memory usage"""
    processes = []
    
    # Iterate through all processes
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
        try:
            # Get process info
            pinfo = proc.info
            processes.append({
                'pid': pinfo['pid'],
                'name': pinfo['name'],
                'memPer': round((pinfo['memory_percent']), 2),
                'cpuPer': round((pinfo['cpu_percent']), 2)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    # Sort by CPU usage (descending) and get top 5
    cpu_top = sorted(processes, key=lambda x: x['cpuPer'], reverse=True)[:5]
    
    # Sort by memory usage (descending) and get top 5
    mem_top = sorted(processes, key=lambda x: x['memPer'], reverse=True)[:5]
    
    # Build the JSON structure
    pcTop = {
        "processes": {
            "cpuTop": {},
            "memTop": {}
        }
    }
    
    # Populate cpuTop
    for i, proc in enumerate(cpu_top):
        pcTop["processes"]["cpuTop"][str(i)] = proc
    
    # Populate memTop
    for i, proc in enumerate(mem_top):
        pcTop["processes"]["memTop"][str(i)] = proc
    
    return pcTop['processes']

pastSent = 0
pastRecv = 0
cpuCores = psutil.cpu_count(logical=False)
cpuThreads = psutil.cpu_count(logical=True)
def pcCollector():
    """Collects system info."""
    global pastSent, pastRecv

    # CPU
    cpu_freq = psutil.cpu_freq()
    pc["cpu"]["freq"] = cpu_freq.current
    pc["cpu"]["percent"] = psutil.cpu_percent(interval=None)
    pc["cpu"]["maxFreq"] = cpu_freq.max
    try:
        pc["cpu"]["temp"] = next(t.current for t in psutil.sensors_temperatures()['k10temp'] if t.label == 'Tctl')
    except Exception:
        pc["cpu"]["temp"] = None
    pc["cpu"]["cores"] = cpuCores
    pc["cpu"]["threads"] = cpuThreads

    # Memory
    mem = psutil.virtual_memory()
    pc["mem"]["total"] = mem.total
    pc["mem"]["available"] = mem.available
    pc["mem"]["used"] = mem.used
    pc["mem"]["percent"] = mem.percent

    # Storage (All mounted disks)
    pc["storage"] = {}
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            pc["storage"][partition.mountpoint] = {
                "device": partition.device,
                "fstype": partition.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent
            }
        except (PermissionError, OSError):
            # Skip partitions that can't be accessed
            pass

    # Network
    net = psutil.net_io_counters()
    pc["network"]["sent"] = net.bytes_sent
    pc["network"]["recv"] = net.bytes_recv
    pc["network"]["sentPerSec"] = net.bytes_sent - pastSent
    pc["network"]["recvPerSec"] = net.bytes_recv - pastRecv
    pastSent, pastRecv = net.bytes_sent, net.bytes_recv

    # GPU
    try:
        for gpu in GPUtil.getGPUs():
            pc["gpu"]["memFree"] = int(gpu.memoryFree * 1_000_000)
            pc["gpu"]["memUsed"] = int(gpu.memoryUsed * 1_000_000)
            pc["gpu"]["percent"] = gpu.load * 100.0
            pc["gpu"]["temp"] = gpu.temperature
    except Exception:
        pc["gpu"] = {"memFree": 0, "memUsed": 0, "percent": 0.0, "temp": 0.0}

    # Other
    pc["bootTime"] = psutil.boot_time()
    pc["processes"] = getProcessInfo()


@app.route("/")
def stats():
    pcCollector()
    return jsonify(pc)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)