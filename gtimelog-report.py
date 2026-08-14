#!/usr/bin/env python3
"""Read and summarise the gtimelog"""
#
# :dotsctl:
#   destdir: ~/bin/
# ...

import argparse
import datetime
import json
import os


def argparser():
    parser = argparse.ArgumentParser(description=__doc__)
    # --clarity=s # not implemented
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "filename",
        nargs="?",
        type=argparse.FileType("r", encoding="utf8"),
    )
    
    args = parser.parse_args()

    if args.filename is None:
        args.filename = open(
            os.path.expanduser("~/.local/share/gtimelog/timelog.txt"),
            "r"
        )

    return args


class Event:
    def __init__(self, start, finish, note):
        if isinstance(start, Event):
            dt_start = start.finish
            self.location = start.location
        else:
            dt_start = start
            self.location = None

        # TODO:
        # - configurable virtual midnight

        # if we cross a virtual midnight then this is the first of the day
        virtual_midnight = finish.replace(hour=2, minute=0)
        if finish < virtual_midnight:
            virtual_midnight = virtual_midnight - datetime.timedelta(days=1)
        if dt_start is not None and dt_start < virtual_midnight:
            dt_start = None
            self.location = None

        self.start = dt_start
        self.finish = finish
        self.note = note
        # TODO: parse note for slacking

        if self.note == "Meta: Start WFH **":
            self.location = "WFH"
        elif self.note == "Meta: Start **":
            self.location = "Other"

    @classmethod
    def from_line(cls, line, start):
        # 2026-08-10 08:54: Meta: Start WFH **
        finish = datetime.datetime.strptime(line[:18], "%Y-%m-%d %H:%M: ")
        note = line[18:]

        return cls(start, finish, note)

    def duration(self):
        """Duration in hours"""
        if self.start is None or self.finish is None:
            return None
        return (self.finish - self.start).total_seconds() / 60 / 60

    def week(self):
        if self.start is None:
            return None
        return self.start.strftime("%G/%V")

    def date(self):
        if self.start is None:
            return None
        return self.start.strftime("%Y-%m-%d")

    def dow(self):
        if self.start is None:
            return None
        return self.start.strftime("%a")

    @property
    def slacking(self):
        if self.note.endswith("**"):
            return True
        else:
            return False

    def __str__(self):
        return f"{self.start}, {self.finish}, {self.duration()}, {self.location}, {self.note}"


class EventMeta:
    def __init__(self, date, name, value):
        self.start = None
        self.finish = date
        self.note = f"#meta {name} {value}"
        self._name = name
        self._value = value

    def week(self):
        return None

    def date(self):
        return None

    def slacking(self):
        return False

    def duration(self):
        return None


class Events:
    def __init__(self):
        self._data = []
        self._totals = {}
        self.daylen = 7.6

    @classmethod
    def from_file(cls, file, debug):
        self = cls()
      
        reference = None

        for line in file:
            line = line.strip()
            if debug:
                print("LINE:", line)

            if line.startswith("#meta"):
                fields = line.split()
                event = EventMeta(reference.finish, fields[1], fields[2])
                self.append(event)
                # TODO:
                # - implement consumer of this data
                #   "#meta overtime_paid $num"
                continue

            if line.startswith("#"):
                continue

            if line == "":
                continue

            event = Event.from_line(line, reference)
            if event.location is None and reference is not None:
                event.location = reference.location

            self.append(event)

            reference = event

        return self

    def append(self, event):
        self._data.append(event)

    def append_fake_now_event(self):
        """Add a synthetic event for right now"""
        e = Event(self._data[-1], datetime.datetime.now(), "_NOW")
        self.append(e)

        # TODO:
        # - A more stable time than now() to assist with testing


    def duration(self):
        """Duration in hours"""
        total = 0.0
        for e in self._data:
            d = e.duration()
            if d is None:
                continue
            total += d
        return total

    def note_len_max(self):
        note_len = 0
        for e in self._data:
            note_len = max(note_len, len(e.note))
        return note_len

    def groupby(self, name):
        r = {}
        for e in self._data:
            attr = getattr(e, name)
            if callable(attr):
                attr = attr()
            if attr is None:
                continue

            if attr not in r:
                r[attr] = Events()
            r[attr].append(e)
        return r

    def print_as_week(self):
        note_len = self.note_len_max()

        dates = self.groupby("date")
        date_names = sorted(dates)

        # First line shows the Date for each column
        print("{0:>{1}}, ".format("Date", note_len), sep="", end="")
        for date in date_names:
            print(f"{date:<10}, ", sep="", end="")
        print("{0:>10}".format("TOTAL"))

        # Second line shows the day shortname
        print("{0:>{1}}, ".format("", note_len), sep="", end="")
        for date in date_names:
            dow = dates[date]._data[0].dow()
            print(f"{dow:<10}, ", sep="", end="")
        print()

        # One line for each task
        notes = self.groupby("note")
        note_values = sorted(notes)
        for note in note_values:
            # first column is the task name
            print("{0:{1}}, ".format(note, note_len), sep="", end="")

            # one column for each day
            note_dates = notes[note].groupby("date")
            for date in date_names:
                if date not in note_dates:
                    print("{0:>10}, ".format(""), sep="", end="")
                else:
                    cell = note_dates[date].duration()
                    print(f"{cell:10.2f}, ", sep="", end="")

            print(f"{notes[note].duration():10.2f}", sep="", end="")
            print()

        # After task totals comes a daily totals for each column
        print()
        print("{0:>{1}}, ".format("WORK", note_len), sep="", end="")
        for date in date_names:
            slacking = dates[date].groupby("slacking")
            try:
                duration = slacking[False].duration()
            except KeyError:
                duration = 0
            print(f"{duration:10.2f}, ", sep="", end="")
        print(f"{self.groupby('slacking')[False].duration():10.2f}")

        print("{0:>{1}}, ".format("TOIL", note_len), sep="", end="")
        toil_sum = 0
        for date in date_names:
            slacking = dates[date].groupby("slacking")
            try:
                working = slacking[False].duration()
            except KeyError:
                working = 0
            toil = working - self.daylen

            # TODO:
            # - calculate toil as overtime on weekday
            # - also need to add weekend processing

            print(f"{toil:10.2f}, ", sep="", end="")
            toil_sum += toil 
        print(f"{toil_sum:10.2f}")

        # Show a "assuming no more slacking, hit option->{day} at $time"
        #
        # TODO:
        # - skip this section if this is not the current week
        print("{0:>{1}}, ".format("WORK UNTIL", note_len), sep="", end="")
        print("TODO")

        # Old clarity option went here
        # it output a new grid table with inflation applied to smear
        # non-job-code work (like the time taken to track your time)

    def print_weeks(self):
        """Splits the events into weeks and prints each one"""
        weeks = self.groupby("week")
        week_names = weeks.keys()
        for week_name in sorted(week_names):
            print("Week", week_name)
            print()
            weeks[week_name].print_as_week()
            print()
            print()

    def print_totals(self):
        r = {}
        r["hours"] = self.duration()
        r["workdays"] = len(self.groupby("date"))
        r["workhours"] = self.groupby("slacking")[False].duration()
        r["hoursperworkday"] = r["workhours"] / r["workdays"]

        # TODO:
        # - toil calculation should take into account weekends
        r["toil"] = r["workhours"] - (self.daylen * r["workdays"])

        r["overtime_paid"] = "FIXME"
        print(json.dumps(r, indent=2, sort_keys=True))


def main():
    args = argparser()

    print(f"Using {args.filename.name} as input file")

    db = Events.from_file(args.filename, debug=args.debug)
    db.append_fake_now_event()

    db.print_weeks()
    print()
    db.print_totals()


if __name__ == "__main__":
    main()
