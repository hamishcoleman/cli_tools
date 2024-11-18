#!/usr/bin/env python3
#
# Given a jinja template filename and one or more yaml files, run the template
#
# :dotsctl:
#   destdir: ~/bin/
#   dpkg:
#     - python3-jinja2
#     - python3-yaml
# ...

import argparse
import jinja2
import yaml


def argparser():
    args = argparse.ArgumentParser(
        description="Run a jinja2 template with some yaml loaded"
    )
    args.add_argument(
        "template",
        type=str,
        help="Jinja2 template file to merge with loaded yaml data and render",
    )
    args.add_argument(
        "yaml",
        nargs="+",
        type=argparse.FileType("r", encoding="utf8"),
        help="YAML File(s) to load data from",
    )
    return args.parse_args()


def main():
    args = argparser()

    # load in the dataset
    db = dict()
    for fh in args.yaml:
        for data in yaml.safe_load_all(fh):
            if isinstance(data, dict):
                db.update(data)
            else:
                # FIXME: use a better key name
                db[fh.name] = data

    # TODO: merge the loaded data, not just dict.update() it
    # TODO: optionally dump the resulting db, for simpler debugging

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader("."),
        extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
    )

    # TODO: the template loader doesnt like relative paths
    # eg: ../jinja2yaml.py ../html/00index.html.j2 00index.yaml
    # raises jinja2.exceptions.TemplateNotFound

    tpl = env.get_template(args.template)

    print(tpl.render(db))


if __name__ == "__main__":
    main()
