#!/usr/bin/env python3
#
# Quick and dirty parser/dumper
#
# :dotsctl:
#   destdir: ~/bin/
# ...

import yaml
import sys
import argparse


def argparser():
    args = argparse.ArgumentParser(
        description="Load a yaml file and then dump it as yaml"
    )
    args.add_argument("--debug",
                      help="Output parsing events in sorted check",
                      default=False,
                      action="store_true",
                      )
    args.add_argument("--raw",
                      help="Also output raw python str()",
                      default=False,
                      action="store_true",
                      )
    args.add_argument("--sorted",
                      help="Check if input has sorted dicts",
                      default=False,
                      action="store_true",
                      )

    args.add_argument(
        "filename",
        type=argparse.FileType("r", encoding="utf8"),
        nargs="*",
    )

    r = args.parse_args()

    if len(r.filename) == 0:
        r.filename.append(sys.stdin)

    return r


def check_sorted(stream, debug=False):
    result = 0
    ctx_stack = []
    ctx = {}
    ctx["index"] = 0

    pop_events = (yaml.SequenceEndEvent, yaml.MappingEndEvent)

    for event in yaml.parse(stream, yaml.SafeLoader):
        if debug:
            print(f"  D1: {ctx_stack}, {ctx}")
            print("    ", event)
            print("    ", event.start_mark)

        index = ctx["index"]
        ctx["index"] += 1

        if isinstance(event, yaml.SequenceStartEvent):
            ctx_stack.append(ctx)
            ctx = {}
            ctx["index"] = 0
            ctx["mod"] = -1  # dont check order in an array context
            continue

        if isinstance(event, yaml.MappingStartEvent):
            ctx_stack.append(ctx)
            ctx = {}
            ctx["index"] = 0
            ctx["mod"] = 2  # even numbers are keys, odd are the values
            continue

        if isinstance(event, pop_events):
            ctx = ctx_stack.pop()
            continue

        if not isinstance(event, yaml.ScalarEvent):
            continue

        # thus this isinstance(event, yaml.ScalarEvent)

        if ctx["mod"] == -1:
            # skip items in this context
            continue

        if index % ctx["mod"] != 0:
            # skip values
            continue

        if "prev" not in ctx:
            ctx["prev"] = None

        if ctx["prev"] is None:
            # We dont have a prev for comparison, so set it and skip
            ctx["prev"] = event.value
            continue

        if ctx["prev"] > event.value:
            result = 1
            print(f"key '{event.value}' should be before '{ctx['prev']}'")
            print(event.start_mark)

        ctx["prev"] = event.value

    return result


class Vault:
    def __init__(self, value):
        self.value = value

    @classmethod
    def representer(cls, dumper, obj):
        return dumper.represent_scalar('!vault', obj.value, style="|")

    @classmethod
    def constructor(cls, loader, node):
        return cls(node.value)


# def yaml_literal(dumper, data):
#   # note that if the representor discovers text that is impossible to
#   # represent with the flow style, it will just revert to a quoted style.
#   # There is no error seen, nor is there a way to force it without mutating
#   # the data.
#   # E.G a space before a newline: " \n"
#
#     if "\n" in data:
#         return dumper.represent_scalar(
#           'tag:yaml.org,2002:str',
#           data,
#           style="|"
#         )
#
#     return dumper.represent_scalar('tag:yaml.org,2002:str', data)
#
#
# yaml.SafeDumper.add_representer(str, yaml_literal)


def main():
    args = argparser()

    yaml.SafeLoader.add_constructor('!vault', Vault.constructor)
    yaml.SafeDumper.add_representer(Vault, Vault.representer)

    result = 0
    for fh in args.filename:
        if args.sorted:
            result += check_sorted(fh, debug=args.debug)
            continue

        db = yaml.safe_load(fh)

        yaml_str = yaml.safe_dump(
            db,
            explicit_start=True,
            explicit_end=True,
            default_flow_style=False,
        )

        if args.raw:
            raw1 = str(db)
            print(raw1)
            print()

        print(yaml_str)

    sys.exit(result)


if __name__ == "__main__":
    main()
