import flask
from flask import request, jsonify

#from scheduler.sched_gen import generate_schedules
from query import query

app = flask.Flask(__name__)
app.config["DEBUG"] = True

qe = query.QueryExecutor()

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

# /api/v1/classes/?term=1770&course=096650
@app.route("/api/v1/classes/", methods=['GET'])
def api_classes():
    args = request.args
    if "term" not in args or "course" not in args:
        return
    term_id, course_id = int(args["term"]), args["course"]
    return jsonify(qe.get_course_classes(term_id, course_id))

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