import logging
import struct
from time import sleep

from dali.driver.base import AsyncDALIDriver
from dali.driver.base import DALIDriver
from dali.driver.base import SyncDALIDriver
from dali.frame import BackwardFrame
from dali.frame import BackwardFrameError

from dali.sequences import sleep as sequence_sleep
from dali.sequences import progress as sequence_progress

import dali.gear.general as gear

import time

import hid

HASSEB_USB_VENDOR = 0x04cc
HASSEB_USB_PRODUCT = 0x0802

HASSEB_READ_FIRMWARE_VERSION    = 0x02
HASSEB_CONFIGURE_DEVICE         = 0x05
HASSEB_DALI_FRAME               = 0X07

HASSEB_DRIVER_NO_DATA_AVAILABLE = 0
HASSEB_DRIVER_NO_ANSWER = 1
HASSEB_DRIVER_OK = 2
HASSEB_DRIVER_INVALID_ANSWER = 3
HASSEB_DRIVER_TOO_EARLY = 4
HASSEB_DRIVER_SNIFFER_BYTE = 5
HASSEB_DRIVER_SNIFFER_BYTE_ERROR = 6


class HassebDALIUSBNoDataAvailable(object):
    def __repr__(self):
        return 'NO DATA AVAILABLE'

    __str__ = __repr__


class HassebDALIUSBNoAnswer(object):
    def __repr__(self):
        return 'NO_ANSWER'

    __str__ = __repr__


class HassebDALIUSBAnswerTooEarly(object):
    def __repr__(self):
        return 'ANSWER_TOO_EARLY'

    __str__ = __repr__


class HassebDALIUSBSnifferByte(object):
    def __repr__(self):
        return 'SNIFFER_BYTE'

    __str__ = __repr__


class HassebDALIUSBSnifferByteError(object):
    def __repr__(self):
        return 'SNIFFER_BYTE_ERROR'

    __str__ = __repr__


class HassebDALIUSBDriver(DALIDriver):
    """``DALIDriver`` implementation for Hasseb DALI USB device.
    """
    device_found = None
    logger = logging.getLogger('HassebDALIUSBDriver')
    sn = 0
    send_message = None
    _pending = None
    _response_message = None

    def __init__(self, path=None):
        try:
            self.device = hid.device()
            if path:
                self.device.open_path(path)
            else:
                self.device.open(HASSEB_USB_VENDOR, HASSEB_USB_PRODUCT)
            self.device_found = 1
        except:
            self.device_found = None

    def run_sequence(self, seq, progress_cb=None):
        from dali.gear.general import EnableDeviceType

        response = None
        try:
            while True:
                try:
                    cmd = seq.send(response)

                except StopIteration as r:
                    return r.value
                if isinstance(cmd, sequence_sleep):
                    time.sleep(cmd.delay)
                elif isinstance(cmd, sequence_progress):
                    if (callable(progress_cb)):
                        progress_cb(cmd)
                else:
                    if cmd.devicetype != 0:
                        self.send(EnableDeviceType(cmd.devicetype))

                    response = self.send(cmd)
        finally:
            seq.close()

    def wait_for_response(self):
        raise NotImplementedError()

    def construct(self, command):
        # sequence number
        self.sn = self.sn+1
        if self.sn > 255:
            self.sn = 1
        frame_length = 16
        if command.is_query:
            expect_reply = 1
        else:
            expect_reply = 0
        transmitter_settling_time = 0
        if command.sendtwice:
            send_twice = 10 # 10 ms delay between messages
        else:
            send_twice = 0
        frame = command.frame.as_byte_sequence
        byte_a, byte_b = frame
        data = struct.pack('BBBBBBBBBB', 0xAA, HASSEB_DALI_FRAME, self.sn,
                           frame_length, expect_reply,
                           transmitter_settling_time, send_twice,
                           byte_a, byte_b,
                           0)
        return data

    def extract(self, data):
        if data == None:
            return None
        elif data[1] == HASSEB_DRIVER_NO_DATA_AVAILABLE:
            # 0: "No Data Available"
            self.logger.debug("No Data Available")
            return HassebDALIUSBNoDataAvailable()
        elif data[1] == HASSEB_DALI_FRAME:
            response_status = data[3]
            if response_status == HASSEB_DRIVER_NO_ANSWER:
                # 1: "No Answer"
                self.logger.debug("No Answer")
                return HassebDALIUSBNoAnswer()
            elif response_status == HASSEB_DRIVER_OK and data[4] == 1:
                # 2: "OK"
                return BackwardFrame(data[5])
            elif response_status == HASSEB_DRIVER_INVALID_ANSWER:
                # 3: "Invalid Answer"
                return BackwardFrameError(255)
            elif response_status == HASSEB_DRIVER_TOO_EARLY:
                # 4: "Answer too early"
                self.logger.debug("Answer too early")
                return HassebDALIUSBAnswerTooEarly()
            elif response_status == HASSEB_DRIVER_SNIFFER_BYTE:
                # 5: "Sniffer byte"
                return HassebDALIUSBSnifferByte()
            elif response_status == HASSEB_DRIVER_SNIFFER_BYTE_ERROR:
                # 6: "Sniffer byte error"
                return HassebDALIUSBSnifferByteError()
        self.logger.error("Invalid Frame")
        return None

    def send(self, command):
        time.sleep(0.02)    # a delay between sent messages need to be at lest 22*417 µs
        self._response_message = None
        data = self.construct(command)
        self.send_message = struct.pack('BB', data[7], data[8])
        if command.response is not None:
            self._pending = command
            self._response_message = None
            self.device.write(data)
            self.wait_for_response()
            return command.response(self.extract(self._response_message))
        else:
            self._pending = None
            self.device.write(data)
            return

    def receive(self):
        data = self.device.read(10)
        frame = self.extract(data)
        if isinstance(frame, HassebDALIUSBNoDataAvailable):
            return
        elif isinstance(frame, BackwardFrame) or isinstance(frame, HassebDALIUSBNoAnswer):
            if self._pending and isinstance(frame, BackwardFrame):
                self._response_message = data
                self._pending = None
            elif self._pending and isinstance(frame, HassebDALIUSBNoAnswer):
                self._response_message = None
                self._pending = None
        return data

    def readFirmwareVersion(self):
        self.sn = self.sn + 1
        if self.sn > 255:
            self.sn = 1
        data = struct.pack('BBBBBBBBBB', 0xAA, HASSEB_READ_FIRMWARE_VERSION,
                            self.sn, 0, 0, 0, 0, 0, 0, 0)
        self.device.write(data)
        data = self.device.read(10)
        for i in range(0,100):
            if len(data)==10:
                if data[1] != HASSEB_READ_FIRMWARE_VERSION:
                    data = self.device.read(10)
                else:
                    return f"{data[3]}.{data[4]}"
            else:
                data = self.device.read(10)
        return f"VERSION_ERROR"

    def enableSniffing(self):
        self.sn = self.sn + 1
        if self.sn > 255:
            self.sn = 1
        data = struct.pack('BBBBBBBBBB', 0xAA, HASSEB_CONFIGURE_DEVICE,
                            self.sn, 0x01, 0, 0, 0, 0, 0, 0)
        self.device.write(data)

    def disableSniffing(self):
        self.sn = self.sn + 1
        if self.sn > 255:
            self.sn = 1
        data = struct.pack('BBBBBBBBBB', 0xAA, HASSEB_CONFIGURE_DEVICE,
                            self.sn, 0, 0, 0, 0, 0, 0, 0)
        self.device.write(data)


class AsyncHassebDALIUSBDriver(HassebDALIUSBDriver, AsyncDALIDriver):
    """Asynchronous ``DALIDriver`` implementation for Hasseb DALI USB device.
       Using asynchronous driver requires a separate thread for receiving
       DALI messages. receive() function needs to be called continously
       from the thread. You can also define an event processor function which
       is called when wating for a response to prevent hangin of the program.
    """

    #def __init__(self, processEvents):
    #    self._processEvents = processEvents

    def setEventHandler(self, processEvents):
        self._processEvents = processEvents

    def wait_for_response(self):
        """Wait for response message. Timeout 2000 ms.
        """
        for i in range(200):
            if not self._pending:
                return
            else:
                self._processEvents()
                time.sleep(0.01)


class SyncHassebDALIUSBDriver(HassebDALIUSBDriver, SyncDALIDriver):
    """Synchronous ``DALIDriver`` implementation for Hasseb DALI USB device.
    """

    def wait_for_response(self):
        """Wait for response message.
        """
        for i in range(200):
            if not self._pending:
                return
            else:
                self.receive()

def SyncHassebDALIUSBDriverFactory():
    """Enumerates Hasseb DALI masters and instantiates `SyncHassebDALIUSBDriver`s
    for each one of them.
    """

    hasseb_dali_drivers = []

    hasseb_hid_devices = hid.enumerate(HASSEB_USB_VENDOR, HASSEB_USB_PRODUCT)
    for hasseb_hid_device in hasseb_hid_devices:
        logging.getLogger("SyncHassebDALIUSBDriverFactory").debug("device found, path is {}".format(hasseb_hid_device.path))
        hasseb_dali_drivers.append(SyncHassebDALIUSBDriver(hasseb_hid_device.path))

    return hasseb_dali_drivers
        

class Device(object):
    """Any DALI slave device that has been configured with a short address."""

    def __init__(self, address, bus=None, randomAddress=None, deviceType=None, groups=None):
        if not isinstance(address, int) or address < 0 or address > 63:
            raise ValueError("address must be an integer in the range 0..63")
        self.address = address
        self.address_obj = Short(address)
        self.bus = None
        if bus:
            self.bind(bus)
        self.randomAddress = randomAddress
        self.deviceType = deviceType
        self.groups = groups

    def bind(self, bus):
        """Bind this device object to a particular DALI bus."""
        bus.add_device(self)


class Bus(object):
    """A DALI bus."""

    _all_addresses = set(range(64))

    def __init__(self, name=None, interface=None):
        self._devices = {}
        self._bus_scanned = False  # Have we scanned the bus for devices?
        self.name = name
        self._interface = interface

    def add_device(self, device):
        if device.bus and device.bus != self:
            print("Device already bound")
        if device.address in self._devices:
            print("Duplicate device")
        if not isinstance(device.address, int) or device.address < 0 \
                or device.address > 63:
            print("Device address is invalid")
        self._devices[device.address] = device
        device.bus = self

    def unused_addresses(self):
        """Return all short addresses that are not in use."""
        used_addresses = set(self._devices.keys())
        return list(self._all_addresses - used_addresses)

    def scan(self):
        """Scan the bus for devices and ensure there are device objects for
        each discovered device.
        """
        i = self.get_interface()
        for sa in range(64):
            if sa in self._devices:
                continue
            response = i.send(QueryControlGearPresent(address.Short(sa)))
            if response.value:
                Device(address=sa, bus=self)
        self._bus_scanned = True

    def set_search_addr(self, addr):
        i = self.get_interface()
        i.send(SetSearchAddrH((addr >> 16) & 0xff))
        i.send(SetSearchAddrM((addr >> 8) & 0xff))
        i.send(SetSearchAddrL(addr & 0xff))

    def find_next(self, low, high):
        """Find the ballast with the lowest random address.  The caller
        guarantees that there are no ballasts with an address lower
        than 'low'.

        If found, returns the random address.  SearchAddr will be set
        to this address in all ballasts.  The ballast is not
        withdrawn.

        If not found, returns None.
        """
        i = self.get_interface()
        self.set_search_addr(high)
        if low == high:
            response = i.send(gear.Compare())
            if response.value is True:
                return low
            return None
        response = i.send(Compare())
        if response.value is True:
            midpoint = (low + high) // 2
            return self.find_next(low, midpoint) \
                or self.find_next(midpoint + 1, high)

    def search_bus(self, broadcast=False):
        """ Initialize bus with broadcast on or off and find the devices from the bus

        """
        addrs = self.unused_addresses()
        i = self.get_interface()
        i.send(Terminate())
        i.send(Initialise(broadcast=broadcast, address=None))
        i.send(Randomise())
        # Randomise may take up to 100ms
        time.sleep(0.1)
        low = 0
        high = 0xffffff
        while low is not None:
            low = self.find_next(low, high)
            if low is not None:
                if addrs:
                    new_addr = addrs.pop(0)
                    i.send(ProgramShortAddress(new_addr))
                    r = i.send(VerifyShortAddress(new_addr))
                    if r.value is not True:
                        print(f"Error in programming short address {new_addr}")
                    i.send(gear.Withdraw())
                    Device(address=new_addr, randomAddress=low, bus=self)
                else:
                    i.send(Terminate())
                    print("No free address")
                low = low + 1
        i.send(Terminate())

    def assign_short_addresses(self):
        """Search for devices on the bus with no short address allocated, and
        allocate each one a short address from the set of unused
        addresses.
        """
        if not self._bus_scanned:
            self.scan()
        self.search_bus(broadcast=False)
        self.query_device_types()
        self.query_groups()

    def initialize_bus(self):
        """Initialize bus
        """
        self._devices = {}
        self.search_bus(broadcast=True)
        self.query_device_types()
        self.query_groups()

    def query_device_types(self):
        """Find the device types of the devices in the bus
        """
        i = self.get_interface()
        for sa in range(64):
            if sa in self._devices:
                self._devices[sa].deviceType = i.send(gear.QueryDeviceType(sa))

    def query_groups(self):
        """Find the groups of the devices in the bus
        """
        i = self.get_interface()
        for sa in range(64):
            if sa in self._devices:
                group1 = i.send(gear.QueryGroupsZeroToSeven(sa))
                group2 = i.send(gear.QueryGroupsEightToFifteen(sa))
                try:
                    group1 = group1.value.as_integer
                    group2 = group2.value.as_integer
                except:
                    self._devices[sa].group = None
                else:
                    self._devices[sa].groups = self.parse_groups(group1, group2)

    def parse_groups(self, group1, group2):
        groups = ""
        if (group1 & 1<<0) != 0:
            groups += "0, "
        if (group1 & 1<<1) != 0:
            groups += "1, "
        if (group1 & 1<<2) != 0:
            groups += "2, "
        if (group1 & 1<<3) != 0:
            groups += "3, "
        if (group1 & 1<<4) != 0:
            groups += "4, "
        if(group1 & 1 << 5) != 0:
            groups += "5, "
        if (group1 & 1 << 6) != 0:
            groups += "6, "
        if (group1 & 1 << 7) != 0:
            groups += "7, "
        if (group2 & 1 << 0) != 0:
            groups += "8, "
        if (group2 & 1 << 1) != 0:
            groups += "9, "
        if (group2 & 1 << 2) != 0:
            groups += "10, "
        if (group2 & 1 << 3) != 0:
            groups += "11, "
        if (group2 & 1 << 4) != 0:
            groups += "12, "
        if (group2 & 1 << 5) != 0:
            groups += "13, "
        if (group2 & 1 << 6) != 0:
            groups += "14, "
        if (group2 & 1 << 7) != 0:
            groups += "15, "
        groups = groups[:-2]

        return groups
