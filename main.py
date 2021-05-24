import flask
from flask import request, jsonify
from flask_cors import CORS, cross_origin
import json
from io import BytesIO

from util import make_local_db
from query import query
from scheduler import sched_gen
from draw import sched_draw
import base64

qe = query.QueryExecutor()
sf = sched_gen.ScheduleFactory()

prefs = {
    "EVENING_CLASSES": False,
    "ONLINE_CLASSES": False,
    "IDEAL_START_TIME": 10,
    "IDEAL_CONSECUTIVE_LENGTH": 2,
    "LIMIT": 10
}

# cmput 174, math 117, math 127, stat 151, wrs 101
#query = qe.get_schedules(1770, "[096650,006776,097174,010807,096909]", 100, sf, sched_draw)

# cmput 174, psyco 104, math 134, stat 151, engl 103
#query = qe.get_schedules(1770, "[096650,009595,106431,010807,106383]", prefs, sf, sched_draw)

query = qe.get_schedules(1770, "[009595]", prefs, sf, sched_draw)

schedules = query["objects"]["schedules"]

import time
for s in schedules:
    sched_draw.draw_schedule(s)
    time.sleep(2)
