import flask
from flask import request, jsonify
from flask_cors import CORS, cross_origin
import json
import time
from io import BytesIO

from util import make_local_db
from query import query
from scheduler import sched_gen
from draw import sched_draw
import base64

qe = query.QueryExecutor()
sf = sched_gen.ScheduleFactory()

# cmput 174, math 117, math 127, stat 151, wrs 101
# [096650,006776,097174,010807,096909]

# cmput 174, psyco 104, math 134, stat 151, engl 103
# [096650,009595,106431,010807,106383]

query = qe.get_schedules(1770, "[001341]", "[1,1,10,3,30]", sf, sched_draw)

schedules = query["objects"]["schedules"]

for s in schedules:
    sched_draw.draw_schedule(s)
    time.sleep(2)
