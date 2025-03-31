#!/usr/bin/env python3
"""Record the interval between events"""
#
# :dotsctl:
#   destdir: ~/bin/
# ...

import argparse
import time


def argparser():
    args = argparse.ArgumentParser(description=__doc__)
    return args.parse_args()


def num2timestr(seconds):
    """Convert a number of seconds into a human time"""

    if seconds == 0:
        return "now"

    days, seconds = divmod(seconds, (60*60*24))
    hours, seconds = divmod(seconds, (60*60))
    minutes, seconds = divmod(seconds, 60)

    fields = 0
    r = []
    if days:
        r += [f"{days}d"]
        fields += 1
    if fields < 2 and hours:
        r += [f"{hours}h"]
        fields += 1
    if fields < 2 and minutes:
        r += [f"{minutes}m"]
        fields += 1
    if fields < 2 and seconds:
        if isinstance(seconds, float):
            r += [f"{seconds:.2}s"]
        else:
            r += [f"{seconds}s"]
        fields += 1
    return "".join(r)


def main():
    args = argparser()

    total = 0
    count = 0
    t1 = time.time()

    while True:
        _ = input()
        t2 = time.time()

        elapsed = t2 - t1
        total += elapsed
        count += 1
        avg = total / count
        t1 = t2

        print(
            f"{int(t2)} {count} {int(total)} {num2timestr(int(elapsed))} {num2timestr(avg)}",
            end = "",
        )


if __name__ == "__main__":
    main()
