# System Monitor Dashboard

A real-time system monitoring dashboard that displays PC metrics on a Raspberry Pi or similar single-board computer. The system consists of two components: a Flask server running on your PC that collects system metrics, and a Rich-based terminal dashboard running on a Raspberry Pi that displays the information.

## Features

- Real-time PC monitoring (CPU, RAM, GPU, Network, Storage)
- Raspberry Pi self-monitoring
- Weather forecast integration
- Top process monitoring (CPU and Memory usage)
- Colorful terminal UI with progress bars and tables
- Auto-refresh display
- Startup/shutdown animations

## Architecture

- **server.py**: Flask server running on your PC that collects and serves system metrics via HTTP
- **main.py**: Terminal dashboard running on Raspberry Pi that fetches and displays metrics

## Requirements

### PC (Server)
- Python 3.7 or higher
- Network connectivity
- GPU (optional, for GPU monitoring)

### Raspberry Pi (Client)
- Python 3.7 or higher
- Network connectivity
- Display connected via HDMI
- Sufficient terminal size (210 columns x 65 lines recommended)

---

## Installation

### Part 1: PC Setup (server.py)

#### 1.1 Install Python Dependencies

First, navigate to your project directory and create a virtual environment:

```bash
cd /path/to/project
python3 -m venv venv
source venv/bin/activate
```

Install required packages:

```bash
pip install flask psutil gputil
```

**NOTE:** The GPUtil package is only required if you have an NVIDIA GPU. If you don't have a GPU or encounter issues, you can modify server.py to skip GPU monitoring.

#### 1.2 Configure the Server

Edit `server.py` if needed. By default, it runs on:
- Host: `0.0.0.0` (all network interfaces)
- Port: `5000`

To change these settings, modify the last line of `server.py`:

```python
app.run(host="0.0.0.0", port=5000)
```

#### 1.3 Test the Server

Start the server manually to verify it works:

```bash
python server.py
```

You should see output like:
```
* Running on http://0.0.0.0:5000
```

Open a browser and navigate to `http://localhost:5000` to verify JSON data is returned.

Press `Ctrl+C` to stop the test server.

#### 1.4 Get Your PC's IP Address

You'll need your PC's local IP address for the Raspberry Pi to connect:

**Linux/macOS:**
```bash
ip a
# or
ifconfig
```

**Windows:**
```cmd
ipconfig
```

Look for your local IP address (usually starts with `192.168.x.x` or `10.x.x.x`).

**NOTE:** Make sure both your PC and Raspberry Pi are on the same network.

#### 1.5 Configure Firewall

Ensure port 5000 is open in your firewall:

**Linux (UFW):**
```bash
sudo ufw allow 5000/tcp
```

**Linux (firewalld):**
```bash
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

**Windows:**
Open Windows Defender Firewall and create an inbound rule for port 5000.

#### 1.6 Set Up Auto-Start on Boot

**For Linux systems using systemd:**

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/pc-monitor.service
```

Add the following content (adjust paths as needed):

```ini
[Unit]
Description=PC System Monitor Server
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/project
Environment="PATH=/path/to/project/venv/bin"
ExecStart=/path/to/project/venv/bin/python /path/to/project/server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**IMPORTANT:** Replace the following:
- `YOUR_USERNAME` with your actual username
- `/path/to/project` with the actual path to your project directory

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pc-monitor.service
sudo systemctl start pc-monitor.service
```

Check the service status:

```bash
sudo systemctl status pc-monitor.service
```

**For Windows:**

1. Convert `server.py` to an executable using PyInstaller:
```cmd
pip install pyinstaller
pyinstaller --onefile server.py
```

2. Create a batch file `start_monitor.bat`:
```batch
@echo off
cd C:\path\to\project
python server.py
```

3. Place a shortcut to this batch file in your Startup folder:
   - Press `Win+R`, type `shell:startup`, press Enter
   - Create a shortcut to your batch file in this folder

---

### Part 2: Raspberry Pi Setup (main.py)

#### 2.1 Install System Dependencies

Update your system:

```bash
sudo apt update
sudo apt upgrade -y
```

Install required system packages:

```bash
sudo apt install -y python3-pip python3-venv figlet
```

#### 2.2 Create Project Directory

```bash
mkdir -p ~/system-monitor
cd ~/system-monitor
```

Copy `main.py` to this directory.

#### 2.3 Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

#### 2.4 Install Python Dependencies

```bash
pip install requests pyfiglet psutil rich
```

**NOTE:** The installation may take several minutes on Raspberry Pi due to limited processing power.

#### 2.5 Configure main.py

Edit `main.py` and update the following configuration variables at the top of the file:

```python
PC_URL = "http://192.168.1.164:5000"  # Change to your PC's IP
API_KEY = "your_weatherapi_key"       # Get from weatherapi.com
LOC = "Your City or Zipcode"          # Your location
```

**To get a Weather API key:**

1. Visit [https://www.weatherapi.com/](https://www.weatherapi.com/)
2. Sign up for a free account
3. Copy your API key from the dashboard
4. Paste it into `main.py`

**TIP:** The free tier allows 1,000,000 API calls per month, which is more than sufficient for this application.

#### 2.6 Adjust Terminal Size

The dashboard is designed for a 210x65 terminal. To adjust your terminal:

**For console (non-GUI):**
```bash
sudo nano /boot/cmdline.txt
```

Add to the end of the line:
```
fbcon=font:VGA8x8
```

Reboot to apply changes.

**For GUI terminal:**
Resize your terminal window and adjust the font size to achieve approximately 210 columns and 65 rows.

**TIP:** You can modify the `columns` and `lines` variables in `main.py` to match your display capabilities.

#### 2.7 Test the Dashboard

Run the dashboard manually:

```bash
cd ~/system-monitor
source venv/bin/activate
python main.py
```

You should see:
1. System initialization messages
2. A startup animation
3. The main dashboard with PC metrics, Pi metrics, weather, and process information

Press `Ctrl+C` to exit gracefully.

**TROUBLESHOOTING:**
- If PC shows as offline, verify the IP address and ensure the server is running
- If weather doesn't load, check your API key and location settings
- If the display is corrupted, adjust your terminal size

#### 2.8 Configure HDMI Power Control

The `hdmiPower()` function in `main.py` controls the display. This may need adjustment based on your hardware.

**For Raspberry Pi 4 and newer:**
The default configuration should work:
```python
def hdmiPower(state: bool):
    value = "0" if state else "1"
    cmd = f"sudo sh -c 'echo {value} > /sys/class/graphics/fb0/blank'"
    subprocess.run(cmd, shell=True, check=True)
```

**For other hardware:**
You may need to use `vcgencmd` instead:
```python
def hdmiPower(state: bool):
    cmd = "vcgencmd display_power 1" if state else "vcgencmd display_power 0"
    subprocess.run(cmd, shell=True, check=True)
```

**IMPORTANT:** To use `hdmiPower()` without entering a password, add sudo permissions:

```bash
sudo visudo
```

Add this line at the end (replace `pi` with your username):
```
pi ALL=(ALL) NOPASSWD: /bin/sh -c echo * > /sys/class/graphics/fb0/blank
```

#### 2.9 Set Up Auto-Start on Boot (CLI Mode)

To run the dashboard in CLI mode at boot (not as a background service):

**Method 1: Using .bashrc (runs in terminal)**

Edit your `.bashrc` file:

```bash
nano ~/.bashrc
```

Add to the end:

```bash
# Auto-start system monitor
if [ -z "$SSH_CLIENT" ] && [ -z "$SSH_TTY" ]; then
    if [ "$(tty)" = "/dev/tty1" ]; then
        cd ~/system-monitor
        source venv/bin/activate
        python main.py
    fi
fi
```

**NOTE:** This only runs on TTY1 (the primary console). It won't run over SSH.

**Method 2: Using systemd with getty (recommended)**

Create a systemd override for getty:

```bash
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
sudo nano /etc/systemd/system/getty@tty1.service.d/override.conf
```

Add:

```ini
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin YOUR_USERNAME --noclear %I $TERM
```

Replace `YOUR_USERNAME` with your Raspberry Pi username.

Then create a script to run at login:

```bash
nano ~/.bash_profile
```

Add:

```bash
if [ "$(tty)" = "/dev/tty1" ]; then
    cd ~/system-monitor
    source venv/bin/activate
    python main.py
fi
```

Enable the service:

```bash
sudo systemctl enable getty@tty1.service
```

**CAUTION:** Auto-login on TTY1 means anyone with physical access can use your system. Only use this on secured devices.

**Method 3: Using rc.local (legacy method)**

Edit rc.local:

```bash
sudo nano /etc/rc.local
```

Add before `exit 0`:

```bash
su - YOUR_USERNAME -c 'cd /home/YOUR_USERNAME/system-monitor && /home/YOUR_USERNAME/system-monitor/venv/bin/python /home/YOUR_USERNAME/system-monitor/main.py > /dev/tty1 2>&1' &
```

Make rc.local executable:

```bash
sudo chmod +x /etc/rc.local
```

**WARNING:** This method runs the script as a background process. For true CLI display, Methods 1 or 2 are preferred.

#### 2.10 Verify Auto-Start

Reboot your Raspberry Pi:

```bash
sudo reboot
```

The dashboard should start automatically after boot completes.

**TROUBLESHOOTING:**
- If the dashboard doesn't appear, check logs: `journalctl -xe`
- Verify the virtual environment path is correct
- Ensure all file paths are absolute in systemd/rc.local configurations

---

## Usage

### Starting/Stopping Services

**PC Server:**

```bash
# Start
sudo systemctl start pc-monitor.service

# Stop
sudo systemctl stop pc-monitor.service

# Restart
sudo systemctl restart pc-monitor.service

# Check status
sudo systemctl status pc-monitor.service

# View logs
sudo journalctl -u pc-monitor.service -f
```

**Raspberry Pi Dashboard:**

If running manually:
```bash
cd ~/system-monitor
source venv/bin/activate
python main.py
```

Exit with `Ctrl+C`.

If running via systemd/auto-start, simply reboot to stop/restart.

### Customizing the Display

**Change welcome message:**

Edit `main.py`, line 208:
```python
textType(pyfiglet.figlet_format("Your Message", width=columns, font="computer", justify="center"), 0.003)
```

**Change terminal size:**

Edit `main.py`, lines 22-23:
```python
columns = 210  # Adjust width
lines = 65     # Adjust height
```

**Add/remove system checks:**

Edit `main.py`, line 82:
```python
systems = ["systemd", "sshd", "cron", "python3", "NetworkManager", "dnsmasq"]
```

**Change update intervals:**

- PC metrics: Line 164 - `time.sleep(1)`  (1 second)
- Weather: Line 197 - `time.sleep(650)`  (≈10 minutes)

---

## Troubleshooting

### PC Server Issues

**Problem:** Server won't start
- Check if port 5000 is already in use: `sudo lsof -i :5000`
- Try a different port by editing `server.py`
- Check Python version: `python3 --version` (needs 3.7+)

**Problem:** GPU monitoring fails
- Install GPU drivers properly
- If no GPU exists, modify `server.py` to skip GPU collection
- Check GPUtil installation: `pip show gputil`

**Problem:** Can't access server from network
- Verify firewall settings
- Ensure both devices are on same network
- Check if server is binding to correct interface

### Raspberry Pi Dashboard Issues

**Problem:** "PC OFFLINE" displayed
- Verify PC server is running: `curl http://PC_IP:5000`
- Check PC_URL in `main.py` matches PC's actual IP
- Ping the PC: `ping PC_IP`
- Check firewall on PC

**Problem:** Weather not loading
- Verify API key is correct
- Check location format (try ZIP code)
- Check internet connectivity: `ping api.weatherapi.com`
- Verify you haven't exceeded API quota

**Problem:** Display is corrupted/misaligned
- Adjust terminal size to 210x65
- Reduce `columns` value in `main.py`
- Try a different font in your terminal
- Ensure terminal supports true color

**Problem:** Temperature readings missing
- On PC: Install `lm-sensors`: `sudo apt install lm-sensors && sudo sensors-detect`
- On Pi: Ensure `cpu_thermal` sensor exists: `cat /sys/class/thermal/thermal_zone*/temp`

**Problem:** Permission denied for HDMI control
- Add sudo permissions as described in section 2.8
- Run with sudo temporarily for testing: `sudo python main.py`

**Problem:** Script won't run on boot
- Check paths in systemd/rc.local are absolute
- Verify virtual environment path exists
- Check logs: `journalctl -xe` or `cat /var/log/syslog`
- Ensure script has executable permissions

---

## Security Considerations

**WARNING:** This system is designed for trusted local networks only.

Security recommendations:

1. **Firewall:** Only allow connections from your local network
   ```bash
   sudo ufw allow from 192.168.1.0/24 to any port 5000
   ```

2. **Authentication:** The server has no authentication. Consider adding Flask-HTTPAuth if exposing beyond LAN

3. **HTTPS:** The connection is unencrypted. For sensitive environments, implement SSL/TLS

4. **Auto-login:** Be cautious with auto-login on Raspberry Pi - anyone with physical access can use the device

5. **API Keys:** Keep your Weather API key private. Don't commit it to public repositories

---

## Performance Tips

**For Raspberry Pi:**

1. Use a lightweight OS (Raspberry Pi OS Lite)
2. Overclock cautiously if needed for smoother rendering
3. Reduce refresh rate if experiencing lag (edit `refresh_per_second` in line 533)
4. Disable unnecessary services to free up resources

**For PC Server:**

1. The server is lightweight and should have minimal impact
2. Adjust collection interval if CPU usage is a concern
3. Consider reducing process count if experiencing slowdown

---

## File Structure

```
system-monitor/
├── server.py           # PC-side Flask server
├── main.py            # Raspberry Pi dashboard client
├── venv/              # Virtual environment (created during setup)
├── README.md          # This file
└── requirements.txt   # Python dependencies (optional)
```

---

## Optional: Creating requirements.txt

For easier dependency management, create requirements files:

**For PC (server):**
```bash
cd /path/to/project
source venv/bin/activate
pip freeze > requirements-server.txt
```

**For Raspberry Pi (client):**
```bash
cd ~/system-monitor
source venv/bin/activate
pip freeze > requirements-client.txt
```

Install from requirements:
```bash
pip install -r requirements-server.txt  # or requirements-client.txt
```

---

## Credits

This project uses the following libraries:
- Flask - Web framework
- psutil - System monitoring
- GPUtil - GPU monitoring
- Rich - Terminal UI
- pyfiglet - ASCII art
- requests - HTTP client

Weather data provided by [WeatherAPI.com](https://www.weatherapi.com/)

---

## License

This project is provided as-is for personal and educational use.

---

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Verify all configuration steps were completed
3. Check system logs for detailed error messages
4. Ensure all dependencies are correctly installed

**TIP:** When debugging, run both `server.py` and `main.py` manually in separate terminals to see real-time error messages.
