database = "Fall_20"


from bs4 import BeautifulSoup
import requests
import sqlite3

def searchCCIDforName(ccid):
    url="https://apps.ualberta.ca/directory/person/"+ccid
    r = requests.get(url)
    data = r.text
    soup = BeautifulSoup(data, "html5lib")
    name = None
    try:
        name = " ".join(soup.h2.get_text().split())
    except:
        print("FAILED for " + ccid)
        return "Unknown"
    remove_creds, _1, _2 = name.partition(',')
    return remove_creds

readconn = sqlite3.connect(database+".db")
rc = readconn.cursor()

writeconn = sqlite3.connect("instructor_names.db")
wc = writeconn.cursor()

wc.execute("CREATE TABLE IF NOT EXISTS names(UID char(16), name text)")

rc.execute("SELECT instructorUid FROM uOfAClass")
for row in rc.fetchall():
    names = row[0]
    if names:
        # if names is a list of instructors then get all names
        instructors = []
        if '[' not in names:
            instructors.append(names)
        else:
            names = names.replace('[', '').replace(']', '').replace("'", '').split(', ')
            for name in names:
                instructors.append(name)
        for name in instructors:
            wc.execute('SELECT EXISTS(SELECT UID FROM names WHERE UID=? LIMIT 1)', (name,))
            exist = wc.fetchone()[0]
            if not exist:
                fullname = searchCCIDforName(name)
                wc.execute("INSERT INTO names (UID, name) VALUES (?, ?)", (name, fullname))
                print("Appended " + name + " --> " + fullname)
                writeconn.commit()
writeconn.commit()
