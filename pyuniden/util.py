#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

module_logger = logging.getLogger('pyuniden')

def zero_to_head(t):
    l = list(t)
    if len(l) is not 10:
        return tuple(l)
    l.insert(0, l[9])
    l.pop(10)

    return tuple(l)

def zero_to_tail(t):
    l = list(t)
    if len(l) is not 10:
        return tuple(l)
    l.insert(9, l[0])
    l.pop(0)

    return tuple(l)

def frq_to_scanner(f):
    module_logger.debug('frq_to_scanner(): f=%s' % f)
    if f == '' or f == 0:
        return f
    l, r = str(f).split('.')
    l = l.rjust(4, '0')
    r = r.ljust(4, '0')
    module_logger.debug('frq_to_scanner(): l=%s,r=%s' % (l, r))

    return ''.join([l, r])

def frq_from_scanner(f):
    f = str(float(f) / 10000)
    l, r = f.split('.')
    r = r.ljust(4, '0')

    return '.'.join([l, r])
