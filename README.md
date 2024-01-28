# PyScreensaver

This project builds a simple screensaver desktop app (using dearpygui) that can be deployed on embedded devices to 
be used as a general display for photos. It was build out of need that a family of a buddy of mine wants to have a smart
device that can display latest family vacation pictures in the living room on a screen. 
It should also auto-update itself with the latest pictures after each run-through. 

Use the `config.yaml` to connect either to an **ftp server** or stream data **locally** from drive (this path could also be a mounted path from shared space).


Install and run:

```bash
sudo apt-get install python3-tk

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt


# edit config.yaml
python gui.py # runs tkinter gui

python dear_gui.py # runs dearpygui (:deprecated needs `pip install dearpygui`)
```


My Current Setup uses the following (not required for this project)

- Webdav

Install:
```bash
sudo apt-get install davfs2
```

Put into /etc/fstab and mount
```bash
# put line into /etc/fstab (sudo required)
<url> <directory> davfs user,rw,auto,errors=remount-ro 0 0

# put line into /etc/davfs2/secrets (sudo required)
<url> <user> <password>

# change privileges of davfs2 secrets file
sudo chmod 600 /etc/davfs2/secrets

# mount directory
sudo mount <url>
```