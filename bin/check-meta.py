#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Device meta data checking tool.
"""

import sys
import argparse
import os
import json
import pprint

__author__ = 'Eric PASCUAL - CSTB (eric.pascual@cstb.fr)'
__copyright__ = 'Copyright (c) 2013 CSTB'
__vcs_id__ = '$Id$'
__version__ = '1.0.0'

def main(args):
    with file(args.infile, 'rt') as infile:
        meta = json.load(infile)
        print("[INFO] meta-data are valid.")
        if args.verbose:
            pprint.pprint(meta)


if __name__ == '__main__':
    _me = sys.modules[__name__]

    def input_file(s):
        if not os.path.exists(s):
            raise argparse.ArgumentTypeError('path not found (%s)' % s)
        if not os.path.isfile(s):
            raise argparse.ArgumentTypeError('path is not a file (%s)' % s)
        return s

    parser = argparse.ArgumentParser(
        description=_me.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        'infile',
        metavar='INFILE',
        help="file to be checked",
        type=input_file
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        default=False,
        help='verbose outputr'
    )

    _args = parser.parse_args()

    try:
        main(_args)
    except Exception as e:
        print('[ERR] %s' % e)
        sys.exit(2)
    else:
        sys.exit(0)

