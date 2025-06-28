#!/usr/bin/env python3
"""Use VT escape codes to figure out what the current terminal size is"""
#
#

import atexit
import os
import sys
import termios

 
CSI = "\x1b["


def savecursor():
    return f"\x1b7"


def restorecursor():
    return f"\x1b8"


def CUP(x, y):
    return f"{CSI}{y};{x}H"


def DSR(n):
    return f"{CSI}{n}n"


def getcursor():
    return DSR(6)


def read_response(end):
    ch = sys.stdin.buffer.read(1)
    if ch != b"\x1b":
        raise ValueError(f"Expected ESC, got {ch}")

    resp = b""
    while True:
        resp += ch
        if ch == end:
            break
        ch = sys.stdin.buffer.read(1)

    return resp


orig = termios.tcgetattr(sys.stdin)
@atexit.register
def _termios_reset():
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, orig)


def termios_set():
    new = termios.tcgetattr(sys.stdin)
    # set lflags
    new[3] = new[3] & ~(termios.ECHO | termios.ICANON)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, new)


def main():
    termios_set()
    print(savecursor(), end="")
    print(CUP(9999,9999), end="")
    print(getcursor(), end="")
    print(restorecursor(), end="")
    sys.stdout.flush()

    resp = read_response(b"R")

    # if debug
    #  print(resp)

    y, x = resp.lstrip(b"\x1b[").rstrip(b"R").split(b";")
    x = int(x)
    y = int(y)
    print(y, x)

    termios.tcsetwinsize(sys.stdin, (y, x))


if __name__ == "__main__":
    main()
