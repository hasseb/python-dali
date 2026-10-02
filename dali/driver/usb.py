import threading
import usb

from dali.driver.base import Backend, Listener


###############################################################################
# USB backends
###############################################################################

class USBBackend(Backend):
    """Backend implementation for communicating with USB devices.
    """

    def __init__(self, vendor, product, bus=None,
                 port_numbers=None, interface=0):
        self._device = None
        # lookup devices by vendor and product
        devices = [dev for dev in usb.core.find(
            find_all=True,
            idVendor=vendor,
            idProduct=product
        )]
        # use first device if bus or port_numers not defined
        if bus is None or port_numbers is None:
            self._device = devices[0]
        else:
            for dev in devices:
                if dev.bus == bus and dev.port_numbers == port_numbers:
                    self._device = dev
                    break
        # if queried device not found, raise
        if not self._device:
            raise usb.core.USBError('Device not found')
        # detach kernel driver if necessary
        if self._device.is_kernel_driver_active(interface) is True:
            self._device.detach_kernel_driver(interface)
        # set device configuration
        self._device.set_configuration()
        # claim interface
        usb.util.claim_interface(self._device, interface)
        # get active configuration
        cfg = self._device.get_active_configuration()
        intf = cfg[(0, 0)]
        # get write end point
        def match_ep_out(e):
            return usb.util.endpoint_direction(e.bEndpointAddress) == \
                   usb.util.ENDPOINT_OUT
        self._ep_write = usb.util.find_descriptor(
            intf, custom_match=match_ep_out)
        # get read end point
        def match_ep_in(e):
            return usb.util.endpoint_direction(e.bEndpointAddress) == \
                   usb.util.ENDPOINT_IN
        self._ep_read = usb.util.find_descriptor(
            intf, custom_match=match_ep_in)

    def read(self, timeout=None):
        """Read data from USB device.
        """
        return self._ep_read.read(self._ep_read.wMaxPacketSize, timeout=timeout)

    def write(self, data):
        """Write data to USB device.
        """
        return self._ep_write.write(data)

    def close(self):
        """Close connection to USB device.
        """
        usb.util.dispose_resources(self._device)


class USBListener(USBBackend, Listener):
    """Listener implementation for communicating with USB devices.
    """

    def __init__(self, driver, vendor, product, bus=None,
                 port_numbers=None, interface=0):
        super(USBListener, self).__init__(
            vendor,
            product,
            bus=bus,
            port_numbers=port_numbers,
            interface=interface
        )
        self.driver = driver
        # flag whether actually disconnecting from device
        self._disconnecting = False
        # event to stop listening
        self._stop_listening = threading.Event()
        # create and start listener thread
        self._listener = threading.Thread(target=self.listen)
        self._listener.start()

    def listen(self):
        """Poll data from USB device.
        """
        while not self._stop_listening.is_set():
            try:
                self.driver.receive(self.read())
            except usb.core.USBError as e:
                # read timeout
                if e.errno == 110:
                    continue
                if not self._disconnecting:
                    self.close()

    def close(self):
        """Close connection to USB device.
        """
        self._disconnecting = True
        self._stop_listening.set()
        super(USBListener, self).close()
