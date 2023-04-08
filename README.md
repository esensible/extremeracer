# Exteme Racer

ExtremeRacer provides a tactical display for sailing:
1. Runs on Raspbery Pi Zero W with Arduino GPS module
2. Supports multiple Kindle Paperwhite for synchronised displays 

The display provides:
* Start sequence
* Speed over water
* Heading
* Precision start (optional)
* VMG (optional)

In addition, its a data logger to help me track, analyse and understand my sailng performance so as to do it better.

## How it works

The application is built on the [SilkFlow](https://github.com/esensible/silkflow) package to implement a super lightweight, reactive web app... in python. There are many packages to do this, including Plotly Dash, but only SilkFlow specifically supports the archane restrictions of the Silk browser available on the Kindle PaperWhite.

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
   * sudo ln -s /home/pi/extremeracer/extremeracer.service /etc/systemd/system
   * sudo systemctl enable extremeracer
