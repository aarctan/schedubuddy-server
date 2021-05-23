import sqlite3
import os
import json
from io import BytesIO
import base64
import numpy as np
from joblib import Parallel, delayed
from cv2 import imread, imdecode, imencode
import zlib

def _imagify(json_sched, draw_schedule_fp):
        image = draw_schedule_fp(json_sched)
        bufferedio = BytesIO()
        image.save(bufferedio, format="PNG")
        base64str = base64.b64encode(bufferedio.getvalue()).decode()
        return base64str

def image_to_base64(json_sched, draw_schedule_fp):
    image = draw_schedule_fp(json_sched)
    image_stream = BytesIO()
    image.save(image_stream, format="PNG")
    image_stream.seek(0)
    file_bytes = np.asarray(bytearray(image_stream.read()), dtype=np.uint8)
    img = imdecode(np.fromstring(file_bytes, np.uint8), 1)
    string = base64.b64encode(imencode('.png', img)[1]).decode()
    return string

class QueryExecutor:
    def __init__(self):
        dirname = os.path.dirname(__file__)
        db_path = os.path.join(dirname, "../local/database.db")
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._cursor = self._conn.cursor()
        uni_format_path = os.path.join(dirname, "../formats/uAlberta.json")
        university_json_f = open(uni_format_path)
        self._uni_json = json.load(university_json_f)
        university_json_f.close()
    
    def get_terms(self):
        term_query = f"SELECT * FROM uOfATerm"
        self._cursor.execute(term_query)
        terms = self._cursor.fetchall()
        json_res = []
        for term in terms:
            json_term = {}
            for k, attr in enumerate(term):
                json_term[self._uni_json["calendar"]["uOfATerm"][k]] = attr
            json_res.append(json_term)
        return {"objects":json_res}
    
    def get_term_courses(self, term:int):
        course_query = f"SELECT * FROM uOfACourse WHERE term=?"
        self._cursor.execute(course_query, (str(term),))
        course_rows = self._cursor.fetchall()
        json_res = []
        for course_row in course_rows:
            json_course = {}
            for k, attr in enumerate(course_row):
                json_course[self._uni_json["calendar"]["uOfACourse"][k]] = attr
            json_res.append(json_course)
        return {"objects":json_res}
    
    def _get_classtimes(self, term:int,c_class:str):
        classtime_query = f"SELECT * FROM uOfAClassTime WHERE term=? AND class=?"
        self._cursor.execute(classtime_query, (str(term), c_class))
        classtime_rows = self._cursor.fetchall()
        json_res = []
        for classtime_row in classtime_rows:
            json_classtime = {}
            for k, attr in enumerate(classtime_row):
                key = self._uni_json["calendar"]["uOfAClassTime"][k]
                if key not in ("term", "course", "class"):
                    json_classtime[key] = attr
            json_res.append(json_classtime)
        return json_res
    
    def get_department_courses(self, term:int, department:str):
        department_query = f"SELECT * FROM uOfACourse WHERE term=? AND departmentCode=?"
        self._cursor.execute(department_query, (str(term), department))
        course_rows = self._cursor.fetchall()
        json_res = []
        for course_row in course_rows:
            json_course = {}
            for k, attr in enumerate(course_row):
                json_course[self._uni_json["calendar"]["uOfACourse"][k]] = attr
            json_res.append(json_course)
        return {"objects":json_res}

    def get_course_classes(self, term:int, course:str, include_online=False):
        class_query = f"SELECT * FROM uOfAClass WHERE term=? AND course=?\
            AND instructionMode!=? AND instructionMode!=?"
        self._cursor.execute(class_query, (str(term), course, "Remote Delivery", "Internet"))
        class_rows = self._cursor.fetchall()
        json_res = []
        for class_row in class_rows:
            json_class = {}
            for k, attr in enumerate(class_row):
                key = self._uni_json["calendar"]["uOfAClass"][k]
                json_class[key] = attr
            json_class["classtimes"] = self._get_classtimes(term, json_class["class"])
            json_res.append(json_class)
        return {"objects":json_res}
    
    def _get_class_obj(self, term:int, class_id:str):
        class_query = f"SELECT * FROM uOfAClass WHERE term=? AND class=?"
        self._cursor.execute(class_query, (str(term), class_id))
        class_row = self._cursor.fetchone()
        json_res = {}
        for k, attr in enumerate(class_row):
            key = self._uni_json["calendar"]["uOfAClass"][k]
            json_res[key] = attr
        json_res["classtimes"] = self._get_classtimes(term, class_id)
        json_res["instructorName"] = self._UID_to_name(json_res["instructorUid"])
        return {"objects":json_res}
    
    def _UID_to_name(self, uid:str):
        if not uid or uid=='':
            return None
        name_query = f"SELECT Name from uOfANames WHERE instructorUid=?"
        self._cursor.execute(name_query, (str(uid),))
        name = self._cursor.fetchone()
        return name[0]
    
    def get_schedules(self, term:int, course_id_list:str, limit, gen_sched, sched_draw):
        # course_id_list is of form: "[######,######,...,######]"
        course_id_list = [str(c) for c in course_id_list[1:-1].split(',')]
        classes = []
        for course_id in course_id_list:
            course_classes = self.get_course_classes(term, course_id)
            classes.append(course_classes)
        sched_obj = gen_sched.generate_schedules({"objects":classes}, int(limit))
        schedules = sched_obj["schedules"]
        json_res = {}
        json_schedules = []
        for schedule in schedules:
            json_sched = []
            for class_id in schedule:
                json_sched.append(self._get_class_obj(term, class_id))
            json_schedules.append(json_sched)
        json_res["schedules"] = json_schedules
        json_res["aliases"] = sched_obj["aliases"]

        results = Parallel(n_jobs=4)(delayed(_imagify)(js, sched_draw.draw_schedule) for js in json_schedules)
        json_res["images"] = results
        '''
        base64images = []
        for json_schedule in json_schedules:
            image = sched_draw.draw_schedule(json_schedule)
            bufferedio = BytesIO()
            image.save(bufferedio, format="PNG")
            base64str = base64.b64encode(bufferedio.getvalue()).decode()
            base64images.append(base64str)
        json_res["images"] = base64images'''

        return {"objects":json_res}
