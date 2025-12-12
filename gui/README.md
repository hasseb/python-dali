hasseb USB DALI Master graphical user interface
===============================================

## Installing development environment and dependencies in Linux

To get python-dali working in Linux Mint 22.2 installation, the following software and python dependencies need to be installed. Python virtual environment needs to be used to install the packages.

sudo apt-get install git
git clone https://github.com/hasseb/python-dali.git
sudo apt-get install python3-pip
sudo apt install python3-distutils
sudo apt install libhidapi-dev
sudo pip3 install setuptools

cd python-dali

sudo python3 setup.py install
sudo pip3 install PyQt5==5.14.0
sudo pip3 install pyusb
sudo pip3 install hid

If you get an "hid.HIDException: unable to open device" Python error, you need to give persmission to open the HID device with the following commands:

1. sudo mkdir -p /etc/udev/rules.d/ echo 'SUBSYSTEMS=="usb", MODE="0666", TAG+="uaccess", TAG+="udev-acl"' | sudo tee /etc/udev/rules.d/92-viia.rules
or
echo 'KERNEL=="hidraw*", SUBSYSTEM=="hidraw", MODE="0666", TAG+="uaccess", TAG+="udev-acl"' | sudo tee /etc/udev/rules.d/92-viia.rules
2. sudo udevadm control --reload-rules
3. sudo udevadm trigger

## Installing development environment and dependencies in Windows  

To get python-dali working in Windows 11, you need to have Python 3.14 or newer installed. The following software and python dependencies need to be installed as well:

pip install setuptools
git clone https://github.com/hasseb/python-dali.git  
cd python-dali/
python setup.py install  
"Add Python/Scripts to Path"  
pip install PyQt5  
pip install pyusb
pip install wheel
pip install Cython
pip install hid
pip install hidapi

To install pyinstaller:
python -m pip install pyinstaller  

To build the Windows installer package, you need to have NSIS installed in your Program Files folder. You need to have EnVar plug-in as well.