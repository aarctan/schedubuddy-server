import flask
from flask import request, jsonify
from flask_cors import CORS, cross_origin
from flask_compress import Compress
import json
from io import BytesIO

from util import make_local_db
from query import query
from scheduler import sched_gen
from draw import sched_draw
import base64

qe = query.QueryExecutor()
sf = sched_gen.ScheduleFactory()

application = flask.Flask(__name__)
cors = CORS(application)
application.config["CORS_HEADERS"] = 'Content-Type'
application.config["DEBUG"] = True


@application.route('/', methods=['GET'])
def api_root():
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

# /api/v1/terms
@application.route("/api/v1/terms", methods=['GET'])
def api_terms():
    return jsonify(qe.get_terms())

# /api/v1/courses/?term=1770
@application.route("/api/v1/courses/", methods=['GET'])
def api_courses():
    args = request.args
    if "term" not in args:
        return
    term_id = int(args["term"])
    return jsonify(qe.get_term_courses(term_id))

# /api/v1/departments/?term=1770&code=COMPUT SCI
@application.route("/api/v1/departments/", methods=['GET'])
def api_departments():
    args = request.args
    if "term" not in args or "code" not in args:
        return
    term_id, department_id = int(args["term"]), args["code"]
    return jsonify(qe.get_department_courses(term_id, department_id))

# /api/v1/classes/?term=1770&course=096650
@application.route("/api/v1/classes/", methods=['GET'])
def api_classes():
    args = request.args
    if "term" not in args or "course" not in args:
        return
    term_id, course_id = int(args["term"]), args["course"]
    return jsonify(qe.get_course_classes(term_id, course_id))

# /api/v1/gen-schedules?term=1770&courses=[096650,006776,097174,010807,096909]&prefs=[1,0,10,3,30]
@application.route("/api/v1/gen-schedules/", methods=['GET'])
def api_gen_schedules():
    args = request.args
    required_args = ("term", "courses", "prefs")
    for required_arg in required_args:
        if required_arg not in args:
            return
    term_id, course_id_list, prefs = int(args["term"]), args["courses"], args["prefs"]
    response = jsonify(qe.get_schedules(term_id, course_id_list, prefs, sf, sched_draw))
    return response

Compress(application)
if __name__ == "__main__":
    application.run()