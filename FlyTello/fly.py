from FlyTello import quicklog, tello, udp
import threading
import time


class Control:
    def __init__(self, sn_map: dict, debug: bool = False):
        """A class for easy tello control."""
        "Log"
        if not debug:
            self.__log = quicklog.create_log(f"Control", 30, False)
        else:
            self.__log = quicklog.create_log(f"Control", 10, True)
        "Init UDP servers"
        self.CommandServer = udp.Server(recv_port=8889, recv_decode=True, send_independent=False, debug=debug)
        self.StatusServer = udp.Server(recv_port=8890, recv_decode=True, send_independent=False, debug=debug)
        self.VideoServer = udp.Server(recv_port=11111, recv_decode=False, send_independent=False, debug=debug)
        self.__log.info("Control: UDP Servers initiated.")
        "Init TelloDB"
        self.TelloDB = tello.TelloDB(sn_map=sn_map, debug=debug)
        self.__log.info("Control: TelloDB initiated.")
        """Scan Tello"""
        self.scan_tello()
        "Init Threads"
        self.__CronJobThread = threading.Thread(target=self.__cronjob)
        self.__CronJobThread.daemon = True
        self.__CronJobThread.start()
        self.__log.info("Control: Cronjob thread initiated.")
        self.__CommandUpdateThread = threading.Thread(target=self.__command_update)
        self.__CommandUpdateThread.daemon = True
        self.__CommandUpdateThread.start()
        self.__log.info("Control: Command update thread initiated.")
        self.__StatusUpdateThread = threading.Thread(target=self.__status_update)
        self.__StatusUpdateThread.daemon = True
        self.__StatusUpdateThread.start()
        self.__log.info("Control: Status update thread initiated.")
        self.__VideoUpdateThread = threading.Thread(target=self.__video_update)
        self.__VideoUpdateThread.daemon = True
        self.__VideoUpdateThread.start()
        self.__log.info("Control: Video update thread initiated.")
        "Exec"
        self.__exec_queue = []
        self.__exec_id = 0
        self.__log.warning(f"Control: Initiated. - [{sn_map}, {debug}]")

    # Basic Functions
    def scan_tello(self):
        """Scan tello in lan."""
        # While haven't found all. Search.
        while not self.TelloDB.query_scan_status():
            # Broadcast to ap mode.
            self.CommandServer.broadcast("command", 8889)
            time.sleep(0.33)
            while self.CommandServer.read_new:
                self.CommandServer.read()
            # Broadcast to ask sn
            self.CommandServer.broadcast("sn?", 8889)
            time.sleep(0.33)
            while self.CommandServer.read_new:
                datagram = self.CommandServer.read()
                self.TelloDB.add_tello(datagram[1][0], datagram[0])
                self.__log.info(f"scan_tello: Passed datagram to TelloDB - {datagram}")
            # Wait for status update
            time.sleep(0.33)
            # List details of tello found.
            print(self.TelloDB.query_object_info())

    def declare_emergency(self):
        """Declare emergency!"""
        self.CommandServer.broadcast("emergency", 8889)  # Prevent drop package
        self.CommandServer.broadcast("emergency", 8889)
        self.CommandServer.broadcast("emergency", 8889)
        self.__log.critical(f"Declared emergency.")

    # Threads
    def __cronjob(self):
        while True:
            datagrams = self.TelloDB.cronjob()
            # Send datagram
            for datagram in datagrams:
                self.CommandServer.send(datagram)
            # Log
            if datagrams:
                self.__log.info(f"Cronjob - Done - {datagrams}")
            time.sleep(0.05)

    def __command_update(self):
        while True:
            while self.CommandServer.read_new:
                self.TelloDB.update_command(self.CommandServer.read())
            time.sleep(0.01)  # Don't hurt my CPU.

    def __status_update(self):
        while True:
            while self.StatusServer.read_new:
                self.TelloDB.update_status(self.StatusServer.read())
            time.sleep(0.01)  # Don't hurt my CPU.

    def __video_update(self):
        while True:
            while self.VideoServer.read_new:
                self.TelloDB.update_video(self.VideoServer.read())
            time.sleep(0.01)  # Don't hurt my CPU.

    # Command Process
    def __cmd2datagram(self, cmd, index):
        """Compose cmd and index into datagram and add to cmd queue."""
        if type(index) == int:
            # Filter invalid index.
            if self.TelloDB.info2info(index=index) is not None:
                self.__exec_queue.append(
                    (cmd, index)
                )
            else:
                self.__log.error(f"cmd2datagram - Can't find tello[{index}]")
        else:
            # Process per command
            for i in index:
                self.__cmd2datagram(cmd, i)

    def exec(self, blocking: bool = True, sync: bool = False, repeat: bool = True, id_fulfil: list = []):
        """
        Execute cmd in exec queue & print result when finished.

        :param blocking: Func exit when task finish.
        :param sync: Ensure all the drones exec the task at the same time.
        :param id_fulfil: If this exist. The task will start when all the task in given list is done.
        :return task_id, a id that can trace is the task finished yet.
        """
        self.__exec_id += 1
        # Pass task to TelloDB
        self.TelloDB.task_add(self.__exec_id, self.__exec_queue, blocking, sync, repeat, id_fulfil)
        self.__log.info(f"Exec - Called TelloDB add task[{self.__exec_id}]. - {self.__exec_queue}, {blocking},"
                        f"{sync}, {id_fulfil}.")
        self.__exec_queue = []
        if not blocking:
            return self.__exec_id
        else:
            while not self.TelloDB.task_status(self.__exec_id):
                time.sleep(0.01)
            return self.__exec_id

    "Basic Control"
    def reboot(self, index):
        self.__cmd2datagram("reboot", index)

    def takeoff(self, index):
        self.__cmd2datagram("takeoff", index)

    def land(self, index):
        self.__cmd2datagram("land", index)

    def stop(self, index):
        self.__cmd2datagram("stop", index)

    def emergency(self, index):
        self.__cmd2datagram("emergency", index)

    def up(self, cm: int, index):
        self.__cmd2datagram(f"up {cm}", index)

    def down(self, cm: int, index):
        self.__cmd2datagram(f"down {cm}", index)

    def left(self, cm: int, index):
        self.__cmd2datagram(f"left {cm}", index)

    def right(self, cm: int, index):
        self.__cmd2datagram(f"right {cm}", index)

    def forward(self, cm: int, index):
        self.__cmd2datagram(f"forward {cm}", index)

    def back(self, cm: int, index):
        self.__cmd2datagram(f"back {cm}", index)

    def clockwise(self, degree: int, index):
        self.__cmd2datagram(f"cw {degree}", index)

    def anti_clockwise(self, degree: int, index):
        self.__cmd2datagram(f"ccw {degree}", index)

    def throwfly(self, index):
        self.__cmd2datagram("throwfly", index)

    def flip(self, direction: str, index):
        self.__cmd2datagram(f"flip {direction}", index)

    "Complex"

    def go(self, x: int, y: int, z: int, speed: int, index):
        self.__cmd2datagram(f"go {x} {y} {z} {speed}", index)

    def curve(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int, index):
        self.__cmd2datagram(f"curve {x1} {y1} {z1} {x2} {y2} {z2} {speed}", index)

    "Pad Related"

    def pad_go(self, x: int, y: int, z: int, speed: int, pad: str, index):
        self.__cmd2datagram(f"go {x} {y} {z} {speed} {pad}", index)

    def pad_curve(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int, pad: str, index):
        self.__cmd2datagram(f"curve {x1} {y1} {z1} {x2} {y2} {z2} {speed} {pad}", index)

    def pad_jump(self, x: int, y: int, z: int, speed: int, yaw: int, pad1: str, pad2: str, index):
        self.__cmd2datagram(f"jump {x} {y} {z} {speed} {yaw} {pad1} {pad2}", index)

    "Setting"

    def set_speed(self, speed: int, index):
        self.__cmd2datagram(f"speed {speed}", index)

    def set_rc(self, roll: int, pitch: int, throttle: int, yaw: int, index):
        self.__cmd2datagram(f"rc {roll} {pitch} {throttle} {yaw}", index)

    def set_wifi(self, ssid: str, password: str, index):
        self.__cmd2datagram(f"wifi {ssid} {password}", index)

    def set_ap(self, ssid: str, password: str, index):
        self.__cmd2datagram(f"ap {ssid} {password}", index)

    def set_wifi_channel(self, channel: int, index):
        self.__cmd2datagram(f"wifisetchannel {channel}", index)

    def set_report_port(self, status_port: int, video_port: int, index):
        self.__cmd2datagram(f"port {status_port} {video_port}", index)

    def set_video_fps(self, quality: str, index):
        self.__cmd2datagram(f"setfps {quality}", index)

    def set_video_bitrate(self, bitrate: int, index):
        self.__cmd2datagram(f"setbitrate {bitrate}", index)

    def set_video_resolution(self, resolution: str, index):
        self.__cmd2datagram(f"setresolution {resolution}", index)

    def set_as_ap(self, ssid: str, password: str, index):
        self.__cmd2datagram(f"multiwifi {ssid} {password}", index)

    "Query"

    def ask_speed(self, index):
        self.__cmd2datagram("speed?", index)

    def ask_battery(self, index):
        self.__cmd2datagram("battery?", index)

    def ask_time(self, index):
        self.__cmd2datagram("time?", index)

    def ask_wifi(self, index):
        self.__cmd2datagram("wifi?", index)

    def ask_sdk(self, index):
        self.__cmd2datagram("sdk?", index)

    def ask_sn(self, index):
        self.__cmd2datagram("sn?", index)

    def ask_hardware(self, index):
        self.__cmd2datagram("hardware?", index)

    def ask_wifiversion(self, index):
        self.__cmd2datagram("wifiversion?", index)

    def ask_ap(self, index):
        self.__cmd2datagram("ap?", index)

    def ask_ssid(self, index):
        self.__cmd2datagram("ssid?", index)

    "Functionality"

    def on_video(self, index):
        self.__cmd2datagram("streamon", index)

    def off_video(self, index):
        self.__cmd2datagram("streamoff", index)

    def on_motor(self, index):
        self.__cmd2datagram("motoron", index)

    def off_motor(self, index):
        self.__cmd2datagram("motoroff", index)

    def on_pad(self, index):
        self.__cmd2datagram("mon", index)

    def off_pad(self, index):
        self.__cmd2datagram("moff", index)

    def on_front_pad_detection(self, index):
        self.__cmd2datagram("mdirection 2", index)

    "EXT"

    def EXT_top_led_static(self, r: int, g: int, b: int, index):
        self.__cmd2datagram(f"EXT led {r} {g} {b}", index)

    def EXT_top_led_breath(self, r: int, g: int, b: int, freq: float, index):
        self.__cmd2datagram(f"EXT led br {freq} {r} {g} {b}", index)

    def EXT_top_led_switch(self, r1: int, g1: int, b1: int, r2: int, g2: int, b2: int, freq: float, index):
        self.__cmd2datagram(f"EXT led bl {freq} {r1} {g1} {b1} {r2} {g2} {b2}", index)

    def EXT_mon_graph(self, graph: str, index):
        self.__cmd2datagram(f"EXT mled g {graph}", index)

    def EXT_mon_word_banner(self, msg: str, direction: str, color: str, freq: float, index):
        self.__cmd2datagram(f"EXT mled {direction} {color} {freq} {msg}", index)

    def EXT_mon_graph_banner(self, graph: str, direction: str, color: str, freq: float, index):
        self.__cmd2datagram(f"EXT mled g {direction} {color} {freq} {graph}", index)

    def EXT_mon_char(self, char: str, color: str, index):
        # P.S. if char == "heart" ==> display heart ^ w ^
        self.__cmd2datagram(f"EXT mled s {color} {char}", index)

    def EXT_mon_default(self, graph: str, index):
        self.__cmd2datagram(f"EXT mled sg {graph}", index)

    def EXT_mon_reset(self, index):
        self.__cmd2datagram("EXT mled sc", index)

    def EXT_mon_brightness(self, brightness: int, index):
        self.__cmd2datagram(f"EXT mled sl {brightness}", index)

    def EXT_read_tof(self, index):
        self.__cmd2datagram("EXT tof?", index)

    def EXT_read_version(self, index):
        self.__cmd2datagram("EXT version?", index)
