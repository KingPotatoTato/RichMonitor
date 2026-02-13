import requests
import pyfiglet
import subprocess
import threading
import shutil
import time
import psutil
import os
import sys
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.align import Align
from rich.console import Group
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text
from rich import box
from io import StringIO

columns = 210  # Fixed for terminal size
lines = 65
console = Console(force_terminal=True, color_system="truecolor", width=columns)

PC_URL = "http://192.168.1.164:5000" # Change to PC's IP (use 'ip a' to find)
API_KEY = "CHANGE ME" # Set to weatherapi API key
LOC = "CHANGE ME" # Set to Zip code or city
API_URL = f"https://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={LOC}&days=2&aqi=no&alerts=yes"

# Global states
pcStatus = False
pc = {}
selfInfo = {
    "cpuPercent": 0.0,
    "memUsed": 0,
    "memTotal": 0,
    "memPercent": 0.0,
    "cpuTemp": 0.0,
    "upTime": 0
}
weather = {}
stopEvent = threading.Event()

def richProgressBar(value: float, min_val: float, max_val: float, width: int = 50) -> str:
    """Simple ASCII progress bar."""
    if value < min_val:
        value = min_val
    elif value > max_val:
        value = max_val

    ratio = (value - min_val) / (max_val - min_val)
    filled = int(ratio * width)
    empty = width - filled
    
    # Color based on percentage
    if ratio < 0.5:
        color = "cyan"
    elif ratio < 0.7:
        color = "green"
    elif ratio < 0.85:
        color = "yellow"
    else:
        color = "red"
    
    bar = "=" * filled + "-" * empty
    return f"[{color}]{bar}[/]"

# Might need to be changed depending on hardware
def hdmiPower(state: bool):
    """Turn HDMI display on or off via /sys/class/graphics/fb0/blank."""
    value = "0" if state else "1"
    cmd = f"sudo sh -c 'echo {value} > /sys/class/graphics/fb0/blank'"
    subprocess.run(cmd, shell=True, check=True)


def checkSystem():
    """Check system services and return status summary."""
    output = {"okay": 0, "fail": 0, "total": 0}

    # Add any other systems
    systems = ["systemd", "sshd", "cron", "python3", "NetworkManager", "dnsmasq"]
    
    print("\n+===================================================+")
    print("|           SYSTEM SERVICE STATUS CHECK             |")
    print("+===================================================+\n")
    
    for proc in systems:
        result = subprocess.run(
            ["pidof", proc],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        if result.returncode == 0:
            print(f"  \033[32m[OK]\033[0m {proc:<30} \033[32m[ONLINE]\033[0m")
            output["okay"] += 1
        else:
            print(f"  \033[31m[XX]\033[0m {proc:<30} \033[31m[OFFLINE]\033[0m")
            output["fail"] += 1
        output["total"] += 1
        time.sleep(0.15)
    
    print("\n" + "-" * 53)
    if output['fail'] > 0:
        print(f"  \033[31m! {output['fail']} system(s) have failed\033[0m")
    print(f"  \033[32m+ {output['okay']} system(s) operational\033[0m")
    print(f"  i Total: {output['total']} services checked")
    print("-" * 53 + "\n")


def textType(text, delay):
    """Type out text character by character with delay."""
    for ch in text:
        sys.stdout.write(f"\033[0m{ch}")
        sys.stdout.flush()
        time.sleep(delay)


def formatBytes(size):
    """Convert bytes to human-readable format with fixed width."""
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if size < 1000:
            return f"{size:05.1f} {unit}"
        size /= 1000
    return f"{size:05.1f} PB"


def floatToColor(value: float, minVal: float, maxVal: float, isPercent=False) -> str:
    """Color mapping."""
    value = max(minVal, min(maxVal, value))
    
    norm = (value - minVal) / (maxVal - minVal) if (maxVal > minVal) else 0.0
    
    # Smoother color gradient
    if norm < 0.4:
        color = "bright_cyan"
    elif norm < 0.6:
        color = "bright_green"
    elif norm < 0.75:
        color = "yellow"
    elif norm < 0.9:
        color = "bright_yellow"
    else:
        color = "bright_red"
    
    if not isPercent:
        return f"[{color}]{value:.1f}[/]"
    else:
        formattedValue = f"{int(value):02d}.{int(value * 10) % 10}"
        return f"[{color}]{formattedValue}[/]"


def pcCollector():
    """Daemon for collecting PC's metrics."""
    global pc, pcStatus
    
    while not stopEvent.is_set():
        try: 
            response = requests.get(PC_URL, timeout=2)
            pc = response.json()
            pcStatus = True
        except (requests.RequestException, ValueError):
            pcStatus = False
        time.sleep(1)


def selfCollector():
    """Daemon for collecting Raspberry Pi's metrics."""
    global selfInfo
    
    while not stopEvent.is_set():
        try:
            mem = psutil.virtual_memory()
            selfInfo["cpuPercent"] = psutil.cpu_percent(interval=1)
            selfInfo["memUsed"] = mem.used
            selfInfo["memTotal"] = mem.total
            selfInfo["memPercent"] = mem.percent
            selfInfo["cpuTemp"] = psutil.sensors_temperatures()['cpu_thermal'][0].current
            selfInfo["upTime"] = psutil.boot_time()
        except (KeyError, IndexError):
            pass


def weatherCollector():
    """Daemon for collecting weather data."""
    global weather
    
    while not stopEvent.is_set():
        try:
            response = requests.get(API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                weather = data
        except (requests.RequestException, ValueError) as e:
            pass
        time.sleep(650)


def startUp():
    """Startup sequence."""
    global weather
    os.system("clear")
    
    # Animated border
    print("\n\033[36m" + "=" * columns + "\033[0m")

    # Change 'Welcome back' to anything you want
    textType(pyfiglet.figlet_format("Welcome back", width=columns, font="computer", justify="center"), 0.003)
    print("\033[36m" + "=" * columns + "\033[0m\n")
    
    time.sleep(2)
    print("\n")
    textType("  > Initializing system diagnostics...\n", 0.08)
    time.sleep(0.3)
    checkSystem()
    time.sleep(4)
    
    print("\n\033[32m  + All systems ready\033[0m")
    time.sleep(1)
    
    # Loading animation
    print("\n  Loading dashboard", end="")
    for _ in range(3):
        time.sleep(0.3)
        print(".", end="", flush=True)
    print("\n")
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            weather = data
    except (requests.RequestException, ValueError) as e:
        pass
    time.sleep(0.5)
    os.system("clear")


def goodbye():
    """Goodbye sequence."""
    os.system("clear")
    print("\n\033[36m" + "=" * columns + "\033[0m")

    # Same with 'Goodbye'
    textType(pyfiglet.figlet_format("Goodbye", width=columns, font="computer", justify="center"), 0.003)
    print("\033[36m" + "=" * columns + "\033[0m\n\n")
    time.sleep(1)
    textType("  > Entering sleep mode in ", 0.05)
    for i in range(3, 0, -1):
        textType(f"{i}...", 0.1)
    print("\n")


def periodicUpdate():
    """Handle PC disconnect/reconnect sequence."""
    global pcStatus
    
    goodbye()
    time.sleep(0.1)
    os.system("clear")
    hdmiPower(False)
    
    while not pcStatus and not stopEvent.is_set():
        time.sleep(1)
    
    hdmiPower(True)
    time.sleep(5)
    os.system("clear")
    startUp()

def formatUptime(seconds: float) -> str:
    """Format uptime in HH:MM format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) / 60)
    return f"{hours:02d}:{minutes:02d}"


def makeLayout():
    """Generate dashboard layout."""
    global pc, pcStatus, selfInfo, weather
    
    layout = Layout()
    layout.split_column(
        Layout(name="banner", size=7),
        Layout(name="body"),
    )
    
    now = time.time()
    localTime = time.localtime(now)
    
    hourInAmPm = time.strftime("%I:%M %p", localTime)
    dayWeek = time.strftime("%A", localTime)
    month = time.strftime("%B %d, %Y", localTime)
    
    # Enhanced banner with status indicator
    statusIndicator = "[green]ONLINE[/]" if pcStatus else "[red]OFFLINE[/]"
    
    bannerLines = [
        f"[bright_cyan]{hourInAmPm}[/]",
        "",
        f"[white]{dayWeek}[/]",
        f"[dim white]{month}[/]",
        f"[dim white]PC Status: {statusIndicator}[/]"
    ]
    bannerText = "\n".join(bannerLines)
    
    layout["banner"].update(
        Panel(
            Align.center(bannerText, vertical="middle"),
            title="[bright_cyan]SYSTEM DASHBOARD[/]",
            border_style="bright_cyan",
            padding=(0, 2),
            box=box.ROUNDED
        )
    )
    
    # Build PC table with enhanced styling
    if pcStatus and pc:
        pcBoot = now - pc.get('bootTime', now)
        pcTable = Table(
            title="PC Info",
            expand=True, 
            box=box.ROUNDED,
            border_style="bright_blue",
            show_header=False,
            padding=(0, 1)
        )
        pcTable.add_column("Metric", justify="left", ratio=2, style="bright_white")
        pcTable.add_column("Value", justify="left", ratio=5)
        
        pcTable.add_row("[bright_cyan]Uptime[/]", f"[bright_white]{formatUptime(pcBoot)}[/]")
        pcTable.add_row("", "")
        pcTable.add_row("[bright_cyan]=== CPU[/]", "")
        pcTable.add_row("  +- Usage", f"{floatToColor(pc['cpu']['percent'], 0, 100, True)}% {richProgressBar(pc['cpu']['percent'], 0, 100, 40)}")
        pcTable.add_row("  +- Frequency", f"{floatToColor(pc['cpu']['freq'], 0, pc['cpu']['maxFreq'] / 1000)} GHz  [dim](Max: {pc['cpu']['maxFreq'] / 1000:.1f} GHz)[/]")
        pcTable.add_row("  +- Temperature", f"{floatToColor(pc['cpu']['temp'], 0, 100)}C")
        pcTable.add_row("", "")
        pcTable.add_row("[bright_cyan]=== GPU[/]", "")
        pcTable.add_row("  +- Usage", f"{floatToColor(pc['gpu']['percent'], 0, 100, True)}% {richProgressBar(pc['gpu']['percent'], 0, 100, 40)}")
        pcTable.add_row("  +- Temperature", f"{floatToColor(pc['gpu']['temp'], 0, 100)}C")
        pcTable.add_row("  +- Memory Used", f"[bright_yellow]{formatBytes(pc['gpu']['memUsed'])}[/]")
        pcTable.add_row("  +- Memory Free", f"[bright_green]{formatBytes(pc['gpu']['memFree'])}[/]")
        pcTable.add_row("", "")
        pcTable.add_row("[bright_cyan]=== RAM[/]", "")
        pcTable.add_row("  +- Usage", f"{floatToColor(pc['mem']['percent'], 0, 100, True)}% {richProgressBar(pc['mem']['percent'], 0, 100, 40)}")
        pcTable.add_row("  +- Used", f"[bright_yellow]{formatBytes(pc['mem']['used'])}[/] / [dim]{formatBytes(pc['mem']['total'])}[/]")
        pcTable.add_row("  +- Available", f"[bright_green]{formatBytes(pc['mem']['available'])}[/]")
        pcTable.add_row("", "")
        pcTable.add_row("[bright_cyan]=== Network[/]", "")
        pcTable.add_row("  +- Total Received", f"[bright_green]{formatBytes(pc['network']['recv'])}[/]")
        pcTable.add_row("  +- Total Sent", f"[bright_blue]{formatBytes(pc['network']['sent'])}[/]")
        pcTable.add_row("  +- Speed Received", f"[bright_green]{formatBytes(pc['network']['recvPerSec'])}/s[/]")
        pcTable.add_row("  +- Speed Sent", f"[bright_blue]{formatBytes(pc['network']['sentPerSec'])}/s[/]")
    else:
        pcTable = Table(expand=True, box=box.ROUNDED, border_style="red", show_header=False)
        pcTable.add_column("Status", justify="center")
        pcTable.add_row("[red]! PC OFFLINE[/]")
        pcTable.add_row("[dim]Waiting for connection...[/]")
    
    # Build Pi table with enhanced styling
    piBoot = now - selfInfo.get('upTime', now)
    piTable = Table(
        title="pi Info",
        expand=True,
        box=box.ROUNDED,
        border_style="bright_magenta",
        show_header=False,
        padding=(0, 1)
    )
    piTable.add_column("Metric", justify="left", ratio=2, style="bright_white")
    piTable.add_column("Value", justify="left", ratio=5)
    
    piTable.add_row("[bright_magenta]Uptime[/]", f"[bright_white]{formatUptime(piBoot)}[/]")
    piTable.add_row("", "")
    piTable.add_row("[bright_magenta]=== CPU[/]", "")
    piTable.add_row("  +- Usage", f"{floatToColor(selfInfo['cpuPercent'], 0, 100, True)}% {richProgressBar(selfInfo['cpuPercent'], 0, 100, 30)}")
    piTable.add_row("  +- Temperature", f"{floatToColor(selfInfo['cpuTemp'], 0, 100)}C")
    piTable.add_row("", "")
    piTable.add_row("[bright_magenta]=== RAM[/]", "")
    piTable.add_row("  +- Usage", f"{floatToColor(selfInfo['memPercent'], 0, 100, True)}% {richProgressBar(selfInfo['memPercent'], 0, 100, 30)}")
    piTable.add_row("  +- Used", f"[bright_yellow]{formatBytes(selfInfo['memUsed'])}[/]")
    piTable.add_row("  +- Total", f"[dim]{formatBytes(selfInfo['memTotal'])}[/]")
    
    # CPU Top Table with enhanced styling
    cpuTable = Table(
        title="[bright_yellow]TOP CPU PROCESSES[/]",
        expand=True,
        box=box.ROUNDED,
        border_style="bright_yellow",
        padding=(0, 1)
    )
    cpuTable.add_column("PID", justify="center", ratio=1, style="cyan")
    cpuTable.add_column("Name", justify="left", ratio=4, style="bright_white")
    cpuTable.add_column("CPU%", justify="right", ratio=1.5, style="yellow")
    cpuTable.add_column("Avg%", justify="right", ratio=1.5, style="dim yellow")
    cpuTable.add_column("MEM%", justify="right", ratio=1.5, style="green")
    
    if pcStatus and pc.get('processes', {}).get('cpuTop'):
        for proc in pc['processes']['cpuTop'].values():
            cpuTable.add_row(
                str(proc['pid']),
                proc['name'][:30],
                f"{proc['cpuPer']:.1f}",
                f"{(proc['cpuPer'] / 32):.1f}",
                f"{proc['memPer']:.1f}",
            )
    
    # Memory Top Table with enhanced styling
    memTable = Table(
        title="[bright_green]TOP MEMORY PROCESSES[/]",
        expand=True,
        box=box.ROUNDED,
        border_style="bright_green",
        padding=(0, 1)
    )
    memTable.add_column("PID", justify="center", ratio=1, style="cyan")
    memTable.add_column("Name", justify="left", ratio=4, style="bright_white")
    memTable.add_column("CPU%", justify="right", ratio=1.5, style="yellow")
    memTable.add_column("Avg%", justify="right", ratio=1.5, style="dim yellow")
    memTable.add_column("MEM%", justify="right", ratio=1.5, style="green")
    
    if pcStatus and pc.get('processes', {}).get('memTop'):
        for proc in pc['processes']['memTop'].values():
            memTable.add_row(
                str(proc['pid']),
                proc['name'][:30],
                f"{proc['cpuPer']:.1f}",
                f"{(proc['cpuPer'] / 32):.1f}",
                f"{proc['memPer']:.1f}",
            )
    
    # Weather Table
    weatherTable = Table(
        title="\nWEATHER FORECAST",
        expand=True,
        box=box.ROUNDED,
        border_style="bright_cyan",
        show_header=False,
        padding=(0, 1)
    )
    weatherTable.add_column("Metric", justify="left", ratio=2, style="bright_white")
    weatherTable.add_column("Value", justify="left", ratio=4)
    
    if weather and 'forecast' in weather and 'current' in weather:
        todayForecast = weather['forecast']['forecastday'][0]
        
        weatherTable.add_row("[bright_cyan]=== Current[/]", "")
        weatherTable.add_row("  +- Temperature", f"[bright_yellow]{weather['current']['temp_c']:.1f}C[/]")
        weatherTable.add_row("  +- Humidity", f"[bright_blue]{weather['current']['humidity']}%[/]")
        weatherTable.add_row("  +- Cloud Cover", f"[dim white]{weather['current']['cloud']}%[/]")
        weatherTable.add_row("  +- Wind Speed", f"[bright_cyan]{weather['current']['wind_mph']:.1f} mph[/]")
        weatherTable.add_row("  +- Precipitation", f"[bright_blue]{weather['current']['precip_mm']:.1f} mm[/]")
        weatherTable.add_row("  +- UV Index", f"[bright_yellow]{weather['current']['uv']:.1f}[/]")
        
        nextHour = min(23, int(time.strftime("%H")) + 1)
        weatherTable.add_row("", "")
        weatherTable.add_row("[bright_cyan]=== Next Hour[/]", "")
        weatherTable.add_row("  +- Temperature", f"[bright_yellow]{todayForecast['hour'][nextHour]['temp_c']:.1f}C[/]")
        weatherTable.add_row("  +- Humidity", f"[bright_blue]{todayForecast['hour'][nextHour]['humidity']}%[/]")
        weatherTable.add_row("  +- Cloud Cover", f"[dim white]{todayForecast['hour'][nextHour]['cloud']}%[/]")
        weatherTable.add_row("  +- Wind Speed", f"[bright_cyan]{todayForecast['hour'][nextHour]['wind_mph']:.1f} mph[/]")
        weatherTable.add_row("  +- Precipitation", f"[bright_blue]{todayForecast['hour'][nextHour]['precip_mm']:.1f} mm[/]")
        weatherTable.add_row("  +- UV Index", f"[bright_yellow]{todayForecast['hour'][nextHour]['uv']:.1f}[/]")
        
        weatherTable.add_row("", "")
        weatherTable.add_row("[bright_cyan]=== Today[/]", "")
        weatherTable.add_row("  +- Max Temp", f"[bright_red]{todayForecast['day']['maxtemp_c']:.1f}C[/]")
        weatherTable.add_row("  +- Min Temp", f"[bright_cyan]{todayForecast['day']['mintemp_c']:.1f}C[/]")
        weatherTable.add_row("  +- Avg Temp", f"[bright_yellow]{todayForecast['day']['avgtemp_c']:.1f}C[/]")
        weatherTable.add_row("  +- Rain Chance", f"[bright_blue]{todayForecast['day']['daily_chance_of_rain']}%[/]")
        weatherTable.add_row("  +- Total Precip", f"[bright_blue]{todayForecast['day']['totalprecip_mm']:.1f} mm[/]")
        
        tomForecast = weather['forecast']['forecastday'][1]
        weatherTable.add_row("", "")
        weatherTable.add_row("[bright_cyan]=== Tomorrow[/]", "")
        weatherTable.add_row("  +- Max Temp", f"[bright_red]{tomForecast['day']['maxtemp_c']:.1f}C[/]")
        weatherTable.add_row("  +- Min Temp", f"[bright_cyan]{tomForecast['day']['mintemp_c']:.1f}C[/]")
        weatherTable.add_row("  +- Avg Temp", f"[bright_yellow]{tomForecast['day']['avgtemp_c']:.1f}C[/]")
        weatherTable.add_row("  +- Rain Chance", f"[bright_blue]{tomForecast['day']['daily_chance_of_rain']}%[/]")
        weatherTable.add_row("  +- Total Precip", f"[bright_blue]{tomForecast['day']['totalprecip_mm']:.1f} mm[/]")
    else:
        weatherTable.add_row("[yellow]Loading weather data...[/yellow]", "")
    
    # Organize panels
    leftColumn = Group(
        pcTable,
        Group(cpuTable, memTable)
    )
    
    rightColumn = Group(
        piTable,
        weatherTable
    )
    
    mainTable = Table(expand=True, box=None, show_header=False, padding=(0, 1))
    mainTable.add_column("Left", justify="center", ratio=1)
    mainTable.add_column("Right", justify="center", ratio=1)
    mainTable.add_row(leftColumn, rightColumn)
    
    layout["body"].update(mainTable)
    
    return layout


def main():
    """Main entry point."""
    print("\n\033[36m" + "═" * columns + "\033[0m")
    print(f"{'SYSTEM INITIALIZATION':^{columns}}")
    print("\033[36m" + "═" * columns + "\033[0m\n")
    
    print("  > Starting daemons...")
    t1 = threading.Thread(target=pcCollector, daemon=True)
    t1.start()
    print("    \033[32m[+]\033[0m PC collector daemon online")
    
    t2 = threading.Thread(target=selfCollector, daemon=True)
    t2.start()
    print("    \033[32m[+]\033[0m Self-info daemon online")
    
    t3 = threading.Thread(target=weatherCollector, daemon=True)
    t3.start()
    print("    \033[32m[+]\033[0m Weather daemon online")
    
    print("\n  > Waiting for data synchronization...")
    time.sleep(2)
    print("    \033[32m[+]\033[0m All systems ready\n")
    
    time.sleep(1)
    startUp()
    
    try:
        with Live(makeLayout(), refresh_per_second=1, console=console, screen=True) as live:
            while True:
                time.sleep(1)
                
                if not pcStatus:
                    live.stop()
                    periodicUpdate()
                    live.start()
                else:
                    live.update(makeLayout())
    except KeyboardInterrupt:
        print("\n\n\033[33m  > Shutting down gracefully...\033[0m")
        stopEvent.set()
        t1.join(timeout=2)
        t2.join(timeout=2)
        t3.join(timeout=2)
        print("  \033[32m[+] All daemons stopped\033[0m")
        print("  \033[32m[+] Shutdown complete\033[0m\n")
        goodbye()


if __name__ == "__main__":
    main()