from FlyTello import quicklog
import select  # Block until data in socket
import socket  # UDP socket
import typing  # Union type support
import threading  # Multi-thread
import time


class Server:
    def __init__(
            self,
            recv_port: int = 8889,
            recv_decode: bool = True,
            send_independent: bool = False,
            debug: bool = False
    ):
        """
        Create a simple udp server.

        :param recv_port: Port to bind.
        :param send_independent: Assign independent socket for send method.
        :param recv_decode: Decode received datagram as utf-8 bytes.
        :param debug: Enter debug mode.
        """
        "Server Info"
        self.__ip = socket.gethostbyname(socket.gethostname())
        self.__debug = debug
        "Log"
        if not debug:
            self.__log = quicklog.create_log(name=f"UDP-{recv_port}", level=30, preserve=False)
        else:
            self.__log = quicklog.create_log(name=f"UDP-{recv_port}", level=10, preserve=True)
        "Recv"
        # #Storage
        self.__recv_data = []
        # #Basic Config
        self.__recv_port = recv_port
        self.__recv_decode = recv_decode
        # #Socket Setup
        self.__recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPV4, UDP
        self.__recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4194304)  # 4MB Socket Buffer
        self.__recv_socket.bind(("0.0.0.0", self.__recv_port))  # Bind to all NIC
        self.__recv_socket.setblocking(False)  # Set non-blocking socket
        self.__log.info("Recv - Socket initiated.")
        # #Thread Setup
        self.__recv_thread = threading.Thread(target=self.__recv)
        self.__recv_thread.daemon = True
        self.__recv_thread.start()
        self.__log.info("Recv - Recv thread initiated.")
        "Send"
        # #Basic Config
        self.__send_independent = send_independent
        # #Socket Setup
        if not self.__send_independent:
            self.__send_socket = self.__recv_socket
        else:
            self.__send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__log.info("Send - Socket initiated.")
        "Read"
        # #Basic Variables
        self.read_new = False  # Indicates new message
        self.__log.warning(f"Server started. [{recv_port}, {send_independent}, {recv_decode}, {debug}]")

    def __recv(self):
        """A internal thread to receive datagram. Datagram format: (bytes, (ip, port))"""
        while select.select([self.__recv_socket], [], [])[0]:  # Block until package in socket
            datagram = []
            # Try get datagram from socket
            try:
                datagram = list(self.__recv_socket.recvfrom(65536))  # Format (bytes, (ip, port))
            except ConnectionResetError:  # Win Err 10054 (Broadcast ICMP Response)
                self.__log.warning("Recv - ConnectionResetError(Maybe due to ICMP report from broadcast failure.)")
            except ConnectionError:
                self.__log.error("Recv - ConnectionError(Check network.)")
            # Filter blank and broadcast datagram
            try:
                if (datagram[0] != b"") and (datagram[1][0] != self.__ip):
                    # Decode on demand
                    if self.__recv_decode:
                        datagram[0] = datagram[0].decode("utf-8", errors="ignore")
                    # Add to storage
                    self.__recv_data.append(datagram)
                    self.__log.info(f"Recv - Received datagram. - {datagram}")
                    # Setup indicator
                    self.read_new = True
            except IndexError:
                pass
        self.__log.critical(f"Recv: Thread exit unexpectedly.")  # Thread shouldn't exit until any scenario.

    def send(self, datagram: typing.Union[tuple, list], internal: bool = False):
        """Send datagram. Datagram format: (bytes, (ip, port))"""
        try:
            self.__send_socket.sendto(datagram[0], datagram[1])
            if not internal:
                self.__log.info(f"Send - Sent datagram. - {datagram}")
        except socket.gaierror:
            print("Error - Send - Check Log.")
            self.__log.error(f"Send - Address Error. - {datagram}")

    def broadcast(self, message: str, port: int):
        """Broadcast a message using dumb way. Tello won't accept the easy one..."""
        message = message.encode("utf-8", errors="ignore")
        ip = self.__ip.split(".")
        messages = [(message, (f"{ip[0]}.{ip[1]}.{ip[2]}.{x}", port)) for x in range(0, 256)]
        for datagram in messages:
            self.send(datagram, internal=True)
        self.__log.info(f"Broadcast - Message broadcasted. - [{message}, {port}, '{ip}']")

    def read(self):
        """Return the latest unread datagram."""
        try:
            # Reset indicator
            if len(self.__recv_data) == 1:
                self.read_new = False
            # Return Data
            return self.__recv_data.pop(0)
        except IndexError:
            self.__log.error("Read - Error Occurs. Func called when not prepared. Pls investigate.")
            # Block until data arrived.
            while len(self.__recv_data) == 0:
                time.sleep(0.05)
            # Reset indicator
            if len(self.__recv_data) == 1:
                self.read_new = False
            # Return Data
            return self.__recv_data.pop()
