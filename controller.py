#!/usr/bin/env python3
"""Plot the live microphone signal(s) with matplotlib.
Matplotlib and NumPy have to be installed.
"""
import time
import socket
import argparse
import random
import queue
import sys
from tools import get_colour_zones_packet, APPLY

RETRIES = 1
UDP_PORT = 56700
SEQ_NUM = random.randint(0, 255)


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')
parser.add_argument(
    '-d', '--device', type=int_or_str,
    help='input device (numeric ID or substring)')
parser.add_argument(
    '-w', '--window', type=float, default=200, metavar='DURATION',
    help='visible time slot (default: %(default)s ms)')
parser.add_argument(
    '-i', '--interval', type=float, default=30,
    help='minimum time between plot updates (default: %(default)s ms)')
parser.add_argument(
    '-b', '--blocksize', type=int, help='block size (in samples)')
parser.add_argument(
    '-r', '--samplerate', type=float, help='sampling rate of audio device')
parser.add_argument(
    '-n', '--downsample', type=int, default=10, metavar='N',
    help='display every Nth sample (default: %(default)s)')
parser.add_argument(
    'channels', type=int, default=[1], nargs='*', metavar='CHANNEL',
    help='input channels to plot (default: the first)')
args = parser.parse_args()
if any(c < 1 for c in args.channels):
    parser.error('argument CHANNEL: must be >= 1')

mapping = [c - 1 for c in args.channels]  # Channel numbers start with 1
q = queue.Queue(64)




def audio_callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    # Fancy indexing with mapping creates a (necessary!) copy:
    q.put(indata[::args.downsample, mapping])


def update_lights(hue):
    """This is called by matplotlib for each plot update.
    Typically, audio callbacks happen more frequently than plot updates,
    therefore the queue tends to contain multiple blocks of audio data.
    """
    while True:
        try:
            data = q.get_nowait()
        except queue.Empty:
            break
        max_amp = max(data)[0] * 500
        if max_amp > 100:
            max_amp = 100
        if max_amp < 1:
            max_amp = 1
        print("amp: {}                 ".format(int(max_amp)), end="\r")
        bulb_ip = "192.168.1.5"
        start_index = 0
        end_index = 11
        sat = 0
        kel = 3500
        packet = get_colour_zones_packet(start_index, end_index,
                                        hue, sat, int(max_amp), kel, APPLY, SEQ_NUM)
        sock.sendto(packet, (bulb_ip, UDP_PORT))





if len(sys.argv) > 0:
    import numpy as np
    import sounddevice as sd
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    if args.samplerate is None:
        device_info = sd.query_devices(args.device, 'input')
        args.samplerate = device_info['default_samplerate']
        
    print("Starting...")
    # start stream
    stream = sd.InputStream(
        device=args.device, channels=max(args.channels),
        samplerate=args.samplerate, callback=audio_callback)
    try:
        with stream:
            hue = 0
            add = 1
            while True:
                # if add:
                #     hue += 0.00005
                #     if hue >= 255:
                #         add = 0
                #         hue = 255
                # else:
                #     hue -= 0.00005
                #     if hue <= 0:
                #         add = 1
                #         hue = 0
                update_lights(int(hue))
    except KeyboardInterrupt as e:
        parser.exit(type(e).__name__ + ': ' + str(e))
else:
    print("No lights with MultiZone capability detected.")
