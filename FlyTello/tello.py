from FlyTello import quicklog  # Logger setup script
import typing  # Union type
import io  # Provide binary stream type


def status_template():
    """Template of status"""
    template = {
        "pad": None,  # Pad no identified
        "pad_x": None,  # x-axis relative to pad(cm)
        "pad_y": None,  # y-axis relative to pad(cm)
        "pad_z": None,  # z-axis relative to pad(cm)
        "pad_pitch": None,  # Pitch relative to pad(degree)
        "pad_roll": None,  # Roll relative to pad(degree)
        "pad_yaw": None,  # Yaw relative to pad(degree)
        "pitch": None,  # Pitch(degree)
        "roll": None,  # Roll(degree)
        "yaw": None,  # Yaw(degree)
        "vgx": None,  # x-axis velocity(m/s)
        "vgy": None,  # y-axis velocity(m/s)
        "vgz": None,  # z-axis velocity(m/s)
        "temp_min": None,  # Minimum temperature recorded since turn on
        "temp_max": None,  # Maximum temperature recorded since turn on
        "tof": None,  # Tof sensor(cn)
        "height": None,  # Height relative to takeoff point(cm)
        "bat": None,  # Battery remains(%)
        "barometer": None,  # Barometer data(m)
        "time": None,  # How long have the motor turns.
        "agx": None,  # Acceleration on x-axis(cms^2)
        "agy": None,  # Acceleration on y-axis(cms^2)
        "agz": None  # Acceleration on z-axis(cms^2)
    }
    return template


def format_status(status: str):
    """Format status from str to dictionary."""
    status = status.split(";")
    # Template
    template = status_template()
    # Process
    for item in status:
        try:
            item = item.split(":")
            if item[0] == "mid":
                template["pad"] = float(item[1])
            elif item[0] == "x":
                template["pad_x"] = float(item[1])
            elif item[0] == "y":
                template["pad_y"] = float(item[1])
            elif item[0] == "z":
                template["pad_z"] = float(item[1])
            elif item[0] == "mpry":
                data = item[1].split(",")
                template["pad_pitch"] = float(data[0])
                template["pad_roll"] = float(data[1])
                template["pad_yaw"] = float(data[2])
            elif item[0] == "pitch":
                template["pitch"] = float(item[1])
            elif item[0] == "roll":
                template["roll"] = float(item[1])
            elif item[0] == "yaw":
                template["yaw"] = float(item[1])
            elif item[0] == "vgx":
                template["vgx"] = float(item[1])
            elif item[0] == "vgy":
                template["vgy"] = float(item[1])
            elif item[0] == "vgz":
                template["vgz"] = float(item[1])
            elif item[0] == "templ":
                template["temp_min"] = float(item[1])
            elif item[0] == "temph":
                template["temp_max"] = float(item[1])
            elif item[0] == "tof":
                template["tof"] = float(item[1])
            elif item[0] == "h":
                template["height"] = float(item[1])
            elif item[0] == "bat":
                template["bat"] = float(item[1])
            elif item[0] == "baro":
                template["barometer"] = float(item[1])
            elif item[0] == "time":
                template["time"] = float(item[1])
            elif item[0] == "agx":
                template["agx"] = float(item[1])
            elif item[0] == "agy":
                template["agy"] = float(item[1])
            elif item[0] == "agz":
                template["agz"] = float(item[1])
        except IndexError:
            pass
        except ValueError:
            pass
    return template


class Tello:
    def __init__(self, ip: str, sn: str, index: int):
        """Tello object - data holder"""
        # Basic Info
        self.__ip = ip
        self.__sn = sn
        self.__index = index
        # Task control related
        self.__cmd = ""
        self.__task_id = 0
        self.__task_done = []
        self.busy = False  # Indicates executing command
        # Control setting
        self.hold = False  # Set to on hold.
        # Status - Ref to official doc
        self.__status = status_template()
        # Video Frame
        self.video_stream = io.BytesIO()

    # Control setting
    def set_hold(self, hold: bool = False):
        """If true, control thread will send stop signal every 5s to prevent auto shutdown."""
        self.hold = hold

    # Task related function
    def task_exec(self, task_id: int, task_cmd: str):
        """Update task info."""
        self.__cmd = task_cmd
        self.__task_id = task_id
        self.busy = True

    def task_exec_result(self, result: str):
        """Update task exec result."""
        # Add record to __task_done
        self.__task_done.append(
            {
                "id": self.__task_id,
                "cmd": self.__cmd,
                "result": result
            }
        )
        # Set indicator
        self.busy = False

    def task_query_status(self, task_id: int):
        """Ask task status."""
        for item in self.__task_done:
            if item["id"] == task_id:
                return True
        return False

    def task_query_result(self, task_id: int):
        """Get task result."""
        for item in reversed(self.__task_done):
            if item["id"] == task_id:
                return item
        return False

    # Get info
    def get_basic_info(self):
        """Get basic info of tello."""
        return {"ip": self.__ip, "sn": self.__sn, "index": self.__index}

    def get_status(self):
        """Get the whole status dictionary."""
        return self.__status

    def get_stream(self):
        """Get the video stream of tello."""
        return self.video_stream

    # Update info
    def update_status(self, status: dict):
        """Update status dictionary with a new one."""
        self.__status = status

    def update_video(self, frame: bytes):
        """Update the video stream."""
        self.video_stream.write(frame)


class TelloDB:
    def __init__(self, sn_map: dict, debug: bool = True):
        """A class to manage tello data and task exec."""
        "Log"
        if not debug:
            self.__log = quicklog.create_log(f"TelloDB", 30, False)
        else:
            self.__log = quicklog.create_log(f"TelloDB", 10, True)
        "Basic"
        self.__sn_map = sn_map  # SN to index dictionary.
        self.__TelloObjects = []  # List holding tello object.
        "Task"
        self.__task_status = {}  # Task id -> Status
        self.__task_done = []  # Task that is done
        self.__task_work = []  # Active task
        "Log"
        self.__log.warning(f"TelloDB - Initiated. - [{sn_map}, {debug}]")

    "CronJob"
    def cronjob(self):
        """Function that regularly called. Check task status & generate command."""
        # Check task status
        for task in self.__task_work:
            # Get task info
            task_id = task["id"]
            tello_index = task["tello"]
            # Determine status
            status = True
            for tello in tello_index:
                tello = self.__info2tello(index=tello)
                status = tello.task_query_status(task_id) and status
                if not status:  # If it is false, no need to check more.
                    break
            # Move task to finish if status.
            if status:
                self.__task_done.append(task)
                self.__task_work.remove(task)
                self.__task_status[task_id] = True
                print(self.task_result(task_id))
        # Generate command
        datagram = []
        for task in self.__task_work:
            ok = True
            # Get task info
            task_id = task["id"]
            task_list = task["task"]
            task_sync = task["sync"]
            tello_index = task["tello"]
            cmd_repeat = task["repeat"]
            id_fulfil = task["id_fulfil"]
            # Determine if id_fulfil is ok
            for id_need in id_fulfil:
                ok = ok and self.task_status(id_need)
                if not ok:
                    break
            # Determine sync is ok
            if task_sync:
                for tello in tello_index:
                    tello = self.__info2tello(index=tello)
                    ok = (not tello.busy) and ok
                    if not ok:
                        break
            # Generate command
            if ok:
                # Generate for task sync
                if task_sync:
                    for item in task_list:
                        # Get task detail
                        tello = self.__info2tello(index=item[1])
                        cmd = item[0]
                        # Add to datagram list
                        if cmd_repeat:
                            datagram.append(
                                (
                                    cmd.encode("utf-8", errors="ignore"),
                                    (tello.get_basic_info()["ip"], 8889)
                                )
                            )
                        datagram.append(
                            (
                                cmd.encode("utf-8", errors="ignore"),
                                (tello.get_basic_info()["ip"], 8889)
                            )
                        )
                        # Setup tello
                        tello.task_exec(task_id, cmd)
                # Generate for non sync task
                else:
                    for item in task_list:
                        # Get task detail
                        tello = self.__info2tello(index=item[1])
                        cmd = item[0]
                        # Not busy & haven't exec command
                        if (not tello.busy) and (not tello.task_query_status(task_id)):
                            # Add to datagram list
                            if cmd_repeat:
                                datagram.append(
                                    (
                                        cmd.encode("utf-8", errors="ignore"),
                                        (tello.get_basic_info()["ip"], 8889)
                                    )
                                )
                            datagram.append(
                                (
                                    cmd.encode("utf-8", errors="ignore"),
                                    (tello.get_basic_info()["ip"], 8889)
                                )
                            )
                            # Setup tello
                            tello.task_exec(task_id, cmd)
        return datagram

    "Task Manage"
    def task_add(self, task_id: int, task_list: list, blocking: bool, sync: bool, repeat: bool, id_fulfil: list):
        """Add task to queue."""
        # Get index of tello that is related
        related_tello_index = [item[1] for item in task_list]
        # Add task item to list
        self.__task_work.append(
            {
                "id": task_id,
                "task": task_list,
                "blocking": blocking,
                "sync": sync,
                "tello": related_tello_index,
                "id_fulfil": id_fulfil,
                "repeat": repeat
            }
        )
        # Add to trace
        self.__task_status[task_id] = False
        # Log
        self.__log.info(f"Task Add - Task added. - [{task_id}, {task_list}, {blocking}, {sync}, {id_fulfil}]")

    def task_status(self, task_id: int):
        """Check task status. True for done, False for not yet."""
        try:
            return self.__task_status[task_id]
        except KeyError:
            self.__log.warning(f"Task Status - Unknown id {task_id}")
            return False

    def task_result(self, task_id: int):
        """Return the result in formatted str."""
        msg = f"\nTask[{task_id}] - Done\n"
        # Get related tello
        index_list = []
        for item in reversed(self.__task_done):
            if item["id"] == task_id:
                index_list = item["tello"]
                break
        # Generate msg
        for tello in index_list:
            tello = self.__info2tello(index=tello)
            task = tello.task_query_result(task_id)
            info = tello.get_basic_info()
            status = tello.get_status()
            msg += f"Tello[{info['index']}] - {status['bat']} - {task['cmd']} - {task['result']}\n"
        return msg

    "Data Manage"
    # Add tello object
    def add_tello(self, ip: str, sn: str):
        # Match index
        index = 1000
        try:
            index = self.__sn_map[sn]
        except KeyError:
            self.__log.error(f"Add tello - Unknown SN - {sn}")
        # Prevent duplicate
        if self.__info2tello(ip=ip) is not None:
            return None
        # Add tello object
        self.__TelloObjects.append(
            Tello(ip, sn, index)
        )
        # Log event
        self.__log.warning(f"Add - Tello added. - ['{ip}', '{sn}', {index}]")

    # Info convert
    def __info2tello(self, ip: str = None, sn: str = None, index: int = None) -> typing.Union[Tello, type(None)]:
        """Return tello that matches all the description."""
        for tello in self.__TelloObjects:
            info = tello.get_basic_info()
            match = True
            # Match IP
            if ip is None:
                match = match and True
            else:
                match = match and (info["ip"] == ip)
            # Match SN
            if sn is None:
                match = match and True
            else:
                match = match and (info["sn"] == sn)
            # Match SN
            if index is None:
                match = match and True
            else:
                match = match and (info["index"] == index)
            # Return
            if match:
                return tello
        return None

    def info2info(self, ip: str = None, sn: str = None, index: int = None):
        """Return the basic info of tello that matches all the description."""
        tello = self.__info2tello(ip, sn, index)
        if tello is None:
            return None
        return tello.get_basic_info()

    def info2status(self, ip: str = None, sn: str = None, index: int = None):
        """Return the status of tello that matches all the description."""
        tello = self.__info2tello(ip, sn, index)
        if tello is None:
            return None
        return tello.get_status()

    def info2stream(self, ip: str = None, sn: str = None, index: int = None):
        """Return the video stream of tello that matches all the description."""
        tello = self.__info2tello(ip, sn, index)
        if tello is None:
            return None
        return tello.get_stream()

    # Update tello object data
    def update_command(self, datagram):
        tello = self.__info2tello(ip=datagram[1][0])
        if tello is None:
            self.__log.warning(f"update_command - Received unknown response from {datagram[1][0]}")
        else:
            tello.task_exec_result(datagram[0])
            self.__log.info(f"update_command - Updated exec result for Tello {tello.get_basic_info()['index']}."
                            f" - {datagram[0]}")

    def update_status(self, datagram):
        tello = self.__info2tello(ip=datagram[1][0])
        if tello is None:
            self.__log.warning(f"update_status - Received unknown status from {datagram[1][0]}")
        else:
            status = format_status(datagram[0])
            tello.update_status(status)
            self.__log.info(f"update_status - Updated status for Tello {tello.get_basic_info()['index']}. - {status}")

    def update_video(self, datagram):
        tello = self.__info2tello(ip=datagram[1][0])
        if tello is None:
            self.__log.warning(f"update_video - Received unknown stream from {datagram[1][0]}")
        else:
            tello.update_video(datagram[0])
            self.__log.info(f"update_status - Updated stream for Tello {tello.get_basic_info()['index']}.")

    # Query TelloDB info
    def query_num_tello(self):
        return len(self.__TelloObjects)

    def query_scan_status(self):
        """Found all the object in sn_map or not."""
        for sn in self.__sn_map:
            if self.__info2tello(sn=sn) is None:
                return False
        return True

    def query_object_info(self):
        """Return formatted info of tello object."""
        msg = "Tello Detail(Discovered): \n"
        for tello in self.__TelloObjects:
            data = tello.get_basic_info()
            status = tello.get_status()
            msg += f"{data['index']} - {status['bat']} - {data['ip']} - {data['sn']}\n"
        return msg

    def query_advance_object_list(self):
        return self.__TelloObjects
