# Intro

I run two Kindle Paperwhites connected to a Raspberry Pi Zero on my Nacra 17 for the following:
* Start sequence
* Early/late indicator so we hit the startline at speed, on the gun
* Speed over water
* Heading

Mostly though, it's a data logger to help me analyse, understand my sailng and ultimately do it better.

I'm using github actions to auto-deploy to the pi on push.

## Pi Setup
1. Install github runner

<!-- 2. sudo visudo 
* ALL=NOPASSWD: /usr/bin/apt-get -->


2. Do the serial setup from the link below
   * https://learn.adafruit.com/adafruit-ultimate-gps-on-the-raspberry-pi/using-uart-instead-of-usb

2. sudo apt update --fix-missing
3. sudo apt install -y uvicorn python3-pip libgeos-dev proj-bin dnsmasq dhcpcd hostapd cron python3-venv    
4. python -m venv /home/pi/venv
4. Deploy application from github
5. Enable extremeracer service to auto-start
   * sudo ln -s /home/pi/pi/extremeracer.service /etc/systemd/system
   * sudo systemctl enable extremeracer
