import flask
from flask import request, jsonify

from query import query
from scheduler import sched_gen

app = flask.Flask(__name__)
app.config["DEBUG"] = True

qe = query.QueryExecutor()
sf = sched_gen.ScheduleFactory()

# /api/v1/terms
@app.route("/api/v1/terms", methods=['GET'])
def api_terms():
    return jsonify(qe.get_terms())

# /api/v1/courses/?term=1770
@app.route("/api/v1/courses/", methods=['GET'])
def api_courses():
    args = request.args
    if "term" not in args:
        return
    term_id = int(args["term"])
    return jsonify(qe.get_term_courses(term_id))

# /api/v1/departments/?term=1770&code=COMPUT SCI
@app.route("/api/v1/departments/", methods=['GET'])
def api_departments():
    args = request.args
    if "term" not in args or "code" not in args:
        return
    term_id, department_id = int(args["term"]), args["code"]
    return jsonify(qe.get_department_courses(term_id, department_id))

# /api/v1/classes/?term=1770&course=096650
@app.route("/api/v1/classes/", methods=['GET'])
def api_classes():
    args = request.args
    if "term" not in args or "course" not in args:
        return
    term_id, course_id = int(args["term"]), args["course"]
    return jsonify(qe.get_course_classes(term_id, course_id))

# api/v1/gen-schedules?term=1770&courses=[096650,006776,097174,010807,096909]
@app.route("/api/v1/gen-schedules/", methods=['GET'])
def api_gen_schedules():
    args = request.args
    if "term" not in args or "courses" not in args:
        return
    term_id, course_id_list = int(args["term"]), args["courses"]
    return jsonify(qe.get_schedules(term_id, course_id_list, sf.generate_schedules))

    

'''
# /api/v1/gen-schedules?query={"courses":["CMPUT 174", "MATH 117", "MATH 127", "STAT 151", "WRS 101"],"term":"Fall_21"}
@app.route('/api/v1/gen-schedules', methods=['GET'])
def api_gen_schedules():
    if 'query' in request.args:
        query = eval(request.args['query'])
        courses_queried = query["courses"]
        (s, a) = generate_schedules(courses_queried)
        return jsonify(s)
    else:
        return "Error: No query provided to gen-schedules."
'''

if __name__ == "__main__":
    app.run()