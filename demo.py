from FlyTello import fly
import signal
import sys

"""
Init Control Program
"""
sn = {
    "0TQDG7KEDBXXXX": 1,
    "0TQDG7KEDBYYYY": 2
}

control = fly.Control(
    sn_map=sn,
    debug=False
)

"""
Setup Emergency - Ctrl + C = Emergency
"""


def emergency(*args):
    print("Terminating.")
    control.declare_emergency()
    sys.exit(0)


signal.signal(signal.SIGINT, emergency)
signal.signal(signal.SIGTERM, emergency)
signal.signal(signal.SIGBREAK, emergency)
input("Press <Enter> to continue.")

"""
Main
"""
# Turn on pad recognition
control.on_pad(index=[1, 2])
control.exec()

control.on_front_pad_detection(index=[1, 2])
control.exec()

control.takeoff(index=1)
control.exec()

control.takeoff(index=2)

control.land(index=[1, 2])
control.exec()
