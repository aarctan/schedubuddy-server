import sqlite3

day_lookup = {'M':0, 'T':1, 'W':2, 'R':3, 'F':4, 'S':5, 'U':6}

def conflict(a,b):
    ranges = []
    for course_class in (a, b):
        start_t, end_t = course_class[6], course_class[7]
        for day in course_class[4]:
            day_mult = day_lookup[day]
            ranges.append((start_t + 2400*day_mult, end_t + 2400*day_mult))
    ranges.sort(key=lambda t: t[0])
    for i in range(len(ranges)-1):
        if ranges[i][1] > ranges[i+1][0]:
            return True
    return False

sqlconn = sqlite3.connect("Fall_21.db")
sqlcursor = sqlconn.cursor()

sqlcursor.execute("DROP TABLE IF EXISTS classTimeConflicts")
sqlcursor.execute("CREATE TABLE IF NOT EXISTS classTimeConflicts(\
p_key text,\
conflicts text)")

sqlcursor.execute("SELECT * FROM uOfAClassTime")
class_times = sqlcursor.fetchall()

conflicts = {}
count = 0
for class_a in class_times:
    class_a_conflicts = []
    a_id = class_a[1]
    for class_b in class_times:
        b_id = class_b[1]
        if conflict(class_a, class_b):
            class_a_conflicts.append(b_id)
    sqlcursor.execute("INSERT INTO classTimeConflicts (p_key, conflicts) VALUES (?, ?)",\
                     (a_id, str(class_a_conflicts)))
    count += 1
    if count % 100 == 0:
        print(count)

sqlconn.commit()
print("\n\nSuccessfully completed.")
sqlconn.close()
