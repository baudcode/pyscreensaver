# PyScreensaver

This project builds a simple screensaver desktop app (using dearpygui) that can be deployed on embedded devices to 
be used as a general display for photos. It was build out of need that a family of a buddy of mine wants to have a smart
device that can display latest family vacation pictures in the living room on a screen. 
It should also auto-update itself with the latest pictures after each run-through. 

Use the `config.yaml` to connect either to an **ftp server** or stream data **locally** from drive (this path could also be a mounted path from shared space).


#### Install and run:



```bash
sudo apt-get install python3-tk

cd /home/pi/
git clone https://github.com/baudcode/pyscreensaver.git
cd pyscreensaver

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# edit config.yaml
python gui.py # runs tkinter gui

# python dear_gui.py # runs dearpygui (:deprecated: needs `pip install dearpygui`)
```

#### Keyboard Shortcuts

- `q` - quit
- `f` - exit fullscreen mode

#### Requirements raspberry pi

```bash
sudo apt-get install libopenblas-dev libjpeg-dev libpng-dev
```

####  Webdav

My Current Setup uses the following (not required for this project)

Install:
```bash
sudo apt-get install davfs2
```
Add user to group
```
sudo usermod -a -G davfs2 pi
```
NOW REBOOT!

Put into /etc/fstab and mount
```bash
# put line into /etc/fstab (sudo required)
<url> <directory> davfs user,rw,autow 0 0

# put line into /etc/davfs2/secrets (sudo required)
<url> <user> <password>

# change privileges of davfs2 secrets file
sudo chmod 600 /etc/davfs2/secrets

# mount directory
sudo mount <url>
```


#### Disable screensaver and add pyscreensaver to autostart

sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
```bash
@xscreensaver -no-splash
@lxterminal -e /home/pi/pyscreensaver/venv/bin/python /home/pi/pyscreensaver/gui.py
```

#### Alternative! method to disable Raspberry PI Screensaver

```bash
sudo raspi-config
```

disable `screen blanking` in the `display settings`.

If that does not work use:
```bash
sudo apt-get install xscreensaver
```

After install, went to Rpi's desktop "Menu" (left top corner)
Went to preference ---> screensaver.
Then In mode : section, selected "disable screensaver" and closed.
Rebooted Rpi.

#### Performance optimization on PI zero

1. Disable automatic updates

```bash
sudo systemctl disable packagekit
```

2. Use i3 window manager (will remove ability)

```bash
sudo apt-get install -y i3
```

- Now change xserver (lightdm) to actually load i3 session

Edit /etc/lightdm/lightdm.conf:

```bash
sudo nano /etc/lightdm/lightdm.conf
```
with
```bash
greeter-session=pi-greeter-labwc
user-session=i3
autologin-session=i3
```

- Autostart the script on i3

Edit `~/.config/i3/config`
and add line

```bash
exec --no-startup-id /home/pi/pyscreensaver/venv/bin/python /home/pi/pyscreensaver/gui.py
```

##### I3 Helper commands:

```
Win+Enter => open terminal
Win+D => start a program by name (filemanger: pcmanfm)
```

Connect to a Wifi Network
```bash
sudo nmcli r wifi on
sudo nmcli dev wifi
sudo nmcli dev wifi connect "SSID" password "PASSWORD"
```