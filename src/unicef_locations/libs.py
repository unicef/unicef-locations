# -*- coding: utf-8 -*-
import random


def get_random_color():
    return '#%02X%02X%02X' % (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )
