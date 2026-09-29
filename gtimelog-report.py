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
        self.finish = finish
        self.note = note

        if isinstance(start, Event):
            self.start = start.finish
            self.location = start.location
        else:
            self.start = start
            self.location = None

        # TODO:
        # - configurable virtual midnight

        # if we cross a virtual midnight then this is the first of the day
        virtual_midnight = finish.replace(hour=2, minute=0)
        if finish < virtual_midnight:
            virtual_midnight = virtual_midnight - datetime.timedelta(days=1)
        if self.start is not None and self.start < virtual_midnight:
            self.start = None
            self.location = None

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
        virtual_midnight = datetime.time(2, 0)
        if self.start.time() < virtual_midnight:
            d = self.start + datetime.timedelta(days=-1)
        else:
            d = self.start
        return d.strftime("%Y-%m-%d")

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
        return ",".join([
            self.start,
            self.finish,
            self.duration(),
            self.location,
            self.note,
        ])


class EventMeta:
    def __init__(self, date, name, value):
        self.start = None
        self.finish = date
        self.note = f"#meta {name} {value}"
        self._name = name
        self._value = float(value)
        self.location = None

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
        self._note_len_max = None
        self._groups = {}

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
            self.append(event)

            reference = event

        return self

    def append(self, event):
        self._data.append(event)
        self._note_len_max = None
        self._groups = {}

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

    def sum_meta(self, name):
        """Add up all the value of meta events with this name"""
        total = 0.0
        for e in self._data:
            if not isinstance(e, EventMeta):
                continue
            if e._name != name:
                continue
            total += e._value
        return total

    def date(self):
        dates = self.groupby("date")
        if len(dates) > 1:
            raise ValueError("Too many dates")
        return self._data[0].date()

    def dow(self):
        dates = self.groupby("date")
        if len(dates) > 1:
            raise ValueError("Too many dates")
        return self._data[0].dow()

    def working_hours(self):
        slacking = self.groupby("slacking")
        try:
            duration = slacking[False].duration()
        except KeyError:
            duration = 0
        return duration

    def toil(self):
        total = 0.0
        try:
            dates = self.groupby("slacking")[False].groupby("date")
        except KeyError:
            return total

        for datestr, date in dates.items():
            # TODO:
            # - hardcoded weekend days
            if date.dow() in ["Sat", "Sun"]:
                daylen = 0
            else:
                daylen = self.daylen

            # TODO:
            # - this feels a little hacky
            # - handle virtual midnight properly
            # - if none toil, could show that clearly
            if str(date.date()) == str(datetime.date.today()):
                # today is not done yet, dont accumulate toil until afterwards
                continue

            total += date.duration() - daylen
        return total

    def note_len_max(self):
        if self._note_len_max is not None:
            return self._note_len_max

        note_len = 0
        for e in self._data:
            note_len = max(note_len, len(e.note))
        self._note_len_max = note_len
        return note_len

    def groupby(self, name):
        if name in self._groups:
            return self._groups[name]

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

        self._groups = r
        return r

    def _attr(self, name):
        """helper to get an attrib value"""
        if name == "":
            # support nullable fields
            return ""

        try:
            attr = getattr(self, name)
        except AttributeError:
            # assume it is supposed to be text
            return name

        if callable(attr):
            attr = attr()
        return attr

    def _row(
            self,
            prefix,
            name,
            suffix,
            note_len=None,
            date_names=None,
            dates=None,
            prefix_just=">"
            ):
        """Print one row of the output matrix, with correct spacing etc"""
        if note_len is None:
            note_len = self.note_len_max()
        print(
            "{0:{2}{1}}, ".format(prefix, note_len, prefix_just),
            sep="",
            end=""
        )

        if dates is None:
            dates = self.groupby("date")
        if date_names is None:
            date_names = sorted(dates)
        for datestr in date_names:
            try:
                date = dates[datestr]
                val = date._attr(name)
            except KeyError:
                val = ""

            if isinstance(val, float):
                print(f"{val:10.2f}, ", sep="", end="")
            else:
                print(f"{val:<10}, ", sep="", end="")

        if suffix is None:
            print()
        else:
            val = self._attr(suffix)
            if isinstance(val, float):
                print(f"{val:10.2f}")
            else:
                print(f"{val:>10}")

    def print_as_week(self):
        # First line shows the Date for each column
        self._row("Date", "date", "TOTAL")
        self._row("", "dow", None)

        # One line for each task
        dates = self.groupby("date")
        date_names = sorted(dates)
        note_len = self.note_len_max()
        notes = self.groupby("note")
        note_values = sorted(notes)
        for note in note_values:
            # first column is the task name
            notes[note]._row(
                note,
                "duration",
                "duration",
                note_len=note_len,
                date_names=date_names,
                dates=notes[note].groupby("date"),
                prefix_just="<",
            )

        # After task totals comes a daily totals for each column
        print()
        self._row("WORK", "working_hours", "working_hours")
        self._row("TOIL", "toil", "toil")

        # Show a "assuming no more slacking, hit option->{day} at $time"
        #
        # TODO:
        # - implement this value
        # - skip this section if this is not the current week
        self._row("WORK UNTIL", "", None)

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

        r["overtime_paid"] = self.sum_meta("overtime_paid")
        r["toil"] = self.toil() - r["overtime_paid"]

        r["locations"] = {}
        for name, events in self.groupby("slacking")[False].groupby("location").items():
            r["locations"][name] = events.duration()

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
