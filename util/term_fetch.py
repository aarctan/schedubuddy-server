term = 1770				# Term code
database = "Fall_21"	# Name of term (this will be the .db file name)
debug = False

# Trying to pull an entire term

print("uAlberta LDAP server database collection with term " + str(term) + " (" + database + ")\n")
from ldap3 import Server, Connection, ALL
import sqlite3
import os
print("Modules loaded. Connecting to LDAP server . . .")

server = Server("directory.srv.ualberta.ca", use_ssl=True)
conn = Connection(server, auto_bind=True, return_empty_attributes=True)
print("Connected. Collecting courses for term " + str(term) + " . . .")

term_search_base = 'term='+str(term)+',ou=calendar,dc=ualberta,dc=ca'
conn.search(term_search_base, '(objectClass=*)', attributes=['*'], paged_size=1000000)
entries = conn.entries
num_entries = len(entries)
print("Collected courses.")

db_file = "./" + database + ".db"
if os.path.isfile(db_file):
	os.remove(db_file)
	print("Pruned old database (" + database + ".db)")
print("Initializing database build . . .")
sqlconn = sqlite3.connect(database+".db")
sqlcursor = sqlconn.cursor()

course_keys = ['course', 'subject', 'catalog', 'facultyCode',
               'faculty', 'departmentCode', 'department',
               'career', 'units', 'courseTitle', 'subjectTitle',
               'courseDescription', 'asString']
sqlcursor.execute("CREATE TABLE IF NOT EXISTS uOfACourse(\
course char(16),\
subject char(16),\
catalog char(16),\
facultyCode char(16),\
faculty text,\
departmentCode char(16),\
department text,\
career char(16),\
units char(16),\
courseTitle text,\
subjectTitle text,\
courseDescription text,\
asString text)")


# There may be multiple instances of some attributes, ie. instructorUid
class_keys = ['course', 'class', 'component', 'section', 'campus',
              'location', 'capacity', 'classType', 'session',
              'instructionMode', 'consent', 'gradingBasis',
              'startDate', 'endDate', 'examStatus', 'examDate',
              'examStartTime', 'examEndTime', 'asString', 'autoEnroll',
              'enrollStatus', 'classStatus', 'classNotes', 'instructorUid']
sqlcursor.execute("CREATE TABLE IF NOT EXISTS uOfAClass(\
course char(16),\
class char(16),\
component char(16),\
section char(16),\
campus char(32),\
location text,\
capacity char(16),\
classType char(16),\
session char(16),\
instructionMode text,\
consent text,\
gradingBasis text,\
startDate text,\
endDate text,\
examStatus text,\
examDate text,\
examStartTime text,\
examEndTime text,\
asString text,\
autoEnroll text,\
enrollStatus text,\
classStatus text,\
classNotes text,\
instructorUid text)")


classtime_keys = ['course', 'class', 'startTime', 'endTime', 'day', 'location', 'start_t', 'end_t']
sqlcursor.execute("CREATE TABLE IF NOT EXISTS uOfAClassTime(\
course char(16),\
class char(16),\
startTime text,\
endTime text,\
day char(16),\
location text,\
start_t integer,\
end_t integer)")


print("\nInitialized database '" + database + ".db'.\nCreating entries for all courses, \
classes, and class times . . .")

def get_numerical_time(str_t):
    h = int(str_t[0:2])
    m = int(str_t[3:5])
    pm = str_t[6:9] == 'PM'
    if pm and h==12: return h*60+m
    if pm and h<12: return (h+12)*60+m
    if not pm and h==12: return m
    if not pm and h<12: return h*60+m
    return None

count=0
batches=0
entries = conn.entries
for entry in entries:
    count+=1
    if(count==100):
        count=0
        batches+=1
        pct = (batches*1.0/num_entries*1.0)*10000
        print(str(pct) + " Percent done")
    
    object_type = str(entry.objectClass)
    
    if object_type=="uOfACourse":
        c=[]
        for key in course_keys:
            value = None
            try:
                value = str(getattr(entry,key))
            except:
                if debug: print("Value not found for course "+str(getattr(entry, "course"))+ " ("+str(getattr(entry, "asString"))+"): mismatch at: " + key)
            c.append(value)
        sqlcursor.execute("INSERT INTO uOfACourse (course, subject, catalog, facultyCode, faculty, departmentCode, department, career, units, courseTitle, subjectTitle, courseDescription, asString) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8], c[9], c[10], c[11], c[12]))
              
    elif object_type=="uOfAClass":
        cc=[]
        for key in class_keys:
            value = None
            try: value = str(getattr(entry,key))
            except:
                if debug: print("Value not found for CLASS "+str(getattr(entry,"class"))+" ("+str(getattr(entry, "asString"))+"): mismatch at: " + key)
            cc.append(value)
        sqlcursor.execute("INSERT INTO uOfAClass (course, class, component, section, campus, location, capacity, classType, session, instructionMode, consent, gradingBasis, startDate, endDate, examStatus, examDate, examStartTime, examEndTime, asString, autoEnroll, enrollStatus, classStatus, classNotes, instructorUid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (cc[0], cc[1], cc[2], cc[3], cc[4], cc[5], cc[6], cc[7], cc[8], cc[9], cc[10], cc[11], cc[12], cc[13], cc[14], cc[15], cc[16], cc[17], cc[18], cc[19], cc[20], cc[21], cc[22], cc[23]))

    elif object_type=="uOfAClassTime":
        ct=[]
        for key in classtime_keys[:-2]:
            value = None
            try: value = str(getattr(entry, key))
            except:
                if debug: print("Value not found for CLASSTIME "+str(getattr(classtime,"class"))+" mismatch at: "+ctkey)
            ct.append(value)
        ct.append(get_numerical_time(ct[2]))
        ct.append(get_numerical_time(ct[3]))
        sqlcursor.execute("INSERT INTO uOfAClassTime (course, class, startTime, endTime, day, location, start_t, end_t) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (ct[0], ct[1], ct[2], ct[3], ct[4], ct[5], ct[6], ct[7]))
    else:
        if debug: print("\n\nUNKNOWN OBJECT_TYPE FOUND: "+object_type+"\n\n")
        
                
sqlconn.commit()
print("\n\nSuccessfully completed.")
sqlconn.close()
