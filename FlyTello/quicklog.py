import os
import time
import logging


def create_log(
        name: str = "",
        level: int = 30,
        preserve: bool = False
):
    """
    Quickly setup individual logger.

    :param name: Name of the logger.
    :param level: Ref: https://docs.python.org/3/library/logging.html#logging-levels
    :param preserve: Give unique name for log file, prevent overwrite.
    :return: Logger object.
    """
    logger = logging.getLogger(name)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(message)s"
    )

    if not os.path.isdir("Log"):
        os.mkdir("Log")

    if preserve:
        path = f"Log//{int(time.time())}//"
        try:
            os.mkdir(path)
        except FileExistsError:
            pass
        handler = logging.FileHandler(f"{path}{name}.log", mode="w", encoding="utf-8",
                                      errors="ignore")
    else:
        handler = logging.FileHandler(f"Log//{name}.log", mode="w+", encoding="utf-8", errors="ignore")
    handler.setFormatter(formatter)

    # Ref Level no. https://docs.python.org/3/library/logging.html#logging-levels
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
