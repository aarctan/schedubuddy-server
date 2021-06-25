import flask
from flask import request, jsonify
from flask_cors import CORS
from flask_compress import Compress
import json
from query import query
from scheduler import sched_gen

qe = query.QueryExecutor()
sf = sched_gen.ScheduleFactory()

app = flask.Flask(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = 'Content-Type'
app.config["DEBUG"] = True

@app.route('/', methods=['GET'])
def api_root():
    return json.dumps({'success':True}), 200, {'ContentType':'app/json'} 

@app.route("/api/v1/terms", methods=['GET'])
def api_terms():
    return jsonify(qe.get_terms())

@app.route("/api/v1/courses/", methods=['GET'])
def api_courses():
    args = request.args
    if "term" not in args:
        return
    term_id = int(args["term"])
    return jsonify(qe.get_term_courses(term_id))

@app.route("/api/v1/classes/", methods=['GET'])
def api_classes():
    args = request.args
    if "term" not in args or "course" not in args:
        return
    term_id, course_id = int(args["term"]), args["course"]
    return jsonify(qe.get_course_classes(term_id, course_id))

@app.route("/api/v1/gen-schedules/", methods=['GET'])
def api_gen_schedules():
    args = request.args
    required_args = ("term", "courses", "prefs")
    for required_arg in required_args:
        if required_arg not in args:
            return
    term_id, course_id_list, prefs = int(args["term"]), args["courses"], args["prefs"]
    response = jsonify(qe.get_schedules(term_id, course_id_list, prefs, sf))
    return response

Compress(app)
if __name__ == "__main__":
    app.run()
    