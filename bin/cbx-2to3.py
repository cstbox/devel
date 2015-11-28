#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Data filter converting CSTBox v2 event logs to v3 format.

Usage: ./cbx-2to3.py < /path/to/input/file > /path/to/output/file
"""

__author__ = 'Eric Pascual - CSTB (eric.pascual@cstb.fr)'

import fileinput
import json

for line in fileinput.input():
    ts, var_type, var_name, value, data = line.split('\t')

    # next 3 lines are specific to Actility box at home files conversion
    if var_name.startswith('home.'):
        var_name = var_name[5:]
    var_name = '.'.join((var_type, var_name))

    data = data.strip().strip('{}')
    if data:
        pairs = data.split(',')
        data = json.dumps(dict([(k.lower(), v) for k, v in (pair.split('=') for pair in pairs)]))
    else:
        data = "{}"

    print('\t'.join((ts, var_type, var_name, value, data)))
