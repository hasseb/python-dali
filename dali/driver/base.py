###############################################################################
# driver contracts
###############################################################################

class DALIDriver:
    """Object for handling wrapped DALI frames sent to and received from
    DALI drivers.

    A DALI driver represents a service or physical gateway which is able to
    communicate with a DALI bus.
    """

    backend = None
    """``Backend`` instance used for reading and writing."""

    def construct(self, command):
        """Construct raw data containing the packed DALI frame from command
        which can be sent to DALI driver.

        @param command: DALI command to send.
        @return data: Returns data which can be sent to backend.
        """
        raise NotImplementedError(
            'Abstract ``DaliDriver`` does not implement ```construct`')

    def extract(self, data):
        """Extract and return DALI Frame from data which has been received
        from DALI driver.

        @param data: Raw data received from gateway.
        @return frame: Returns ``dali.frame.Frame`` deriving object.
        """
        raise NotImplementedError(
            'Abstract ``DaliDriver`` does not implement ``extract``')


class SyncDALIDriver(DALIDriver):
    """Object for synchronously sending data to DALI drivers immediately
    expecting and returning a result.
    """

    def send(self, command, timeout=None):
        """Send command to gateway and return response.

        @param command: DALI command to send.
        @param timeout: Timeout in milliseconds.
        @return response: response to command.
        """
        raise NotImplementedError(
            'Abstract ``SyncDALIDriver`` does not implement ``send``')


class AsyncDALIDriver(DALIDriver):
    """Object for asynchronously handling data sent to and received from
    DALI drivers.
    """

    dispatcher = None
    """Callable used for dispatching incoming forward frames.
    """

    def send(self, command, callback=None, **kw):
        """Send command to gateway.

        @param command: DALI command to send.
        @param callback: Function which gets called with received response.
        @param **kw: Optional keyword arguments which get passed to response
                     callback
        """
        raise NotImplementedError(
            'Abstract ``AsyncDALIDriver`` does not implement ``send``')

    def receive(self, frame):
        """Receive DALI Frame.

        If a forward frame is received, ``self.dispatcher`` is used for
        delegating it.

        If a backward frame is received, the ``callback`` given in
        ``self.send`` is used.

        @param frame: ``dali.frame.Frame`` deriving object.
        """
        raise NotImplementedError(
            'Abstract ``AsyncDALIDriver`` does not implement ``receive``')


###############################################################################
# backend contracts
###############################################################################

class Backend:
    """Object representing a backend.
    """

    def read(self, timeout=None):
        raise NotImplementedError(
            'Abstract ``Backend`` does not implement ``read``')

    def write(data):
        raise NotImplementedError(
            'Abstract ``Backend`` does not implement ``write``')

    def close(self):
        raise NotImplementedError(
            'Abstract ``Backend`` does not implement ``close``')


class Listener(Backend):
    """Object representing a backend which is permanently listening for
    incoming frames.
    """

    driver = None
    """``AsyncDALIDriver`` instance.
    """

    def listen(self):
        """Listen to backend and dispatch receiced data to ``self.driver``.
        """
        raise NotImplementedError(
            'Abstract ``Listener`` does not implement ``listen``')
