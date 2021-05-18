import flask
from flask import request, jsonify
import json

from util import make_local_db
make_local_db.fetch_all(flush=True)

from query import query
from scheduler import sched_gen

qe = query.QueryExecutor()
sf = sched_gen.ScheduleFactory()

application = flask.Flask(__name__)
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

# api/v1/gen-schedules?term=1770&courses=[096650,006776,097174,010807,096909]
@application.route("/api/v1/gen-schedules/", methods=['GET'])
def api_gen_schedules():
    args = request.args
    if "term" not in args or "courses" not in args:
        return
    term_id, course_id_list = int(args["term"]), args["courses"]
    return jsonify(qe.get_schedules(term_id, course_id_list, sf.generate_schedules))

if __name__ == "__main__":
    application.run()