import flask
from flask import request, jsonify

import sched_gen

app = flask.Flask(__name__)
app.config["DEBUG"] = True

# /api/v1/gen-schedules?query={"courses":["CMPUT 174", "MATH 117", "MATH 127", "STAT 151", "WRS 101"],"term":"Fall_21"}
@app.route('/api/v1/gen-schedules', methods=['GET'])
def api_id():
    if 'query' in request.args:
        query = eval(request.args['query'])
        courses_queried = query["courses"]
        (s, a) = sched_gen.generate_schedules(courses_queried)
#        json_schedules = [sched._schedule for sched in s]
        return jsonify(s)
    else:
        return "Error: No query provided to gen-schedules."

app.run()