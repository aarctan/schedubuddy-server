import json, ldap3, sqlite3, logging, sys, os, datetime, requests
from bs4 import BeautifulSoup

# Set logging level to at least INFO to disable debug messages.
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

dirname = os.path.dirname(__file__)
uni_format_path = os.path.join(dirname, "../formats/uAlberta.json")
university_json_f = open(uni_format_path)
university_json = json.load(university_json_f)
university_json_f.close()

SEARCH_PREFIX = "ou=calendar,dc=ualberta,dc=ca"
server = ldap3.Server(university_json["server"])
ldap_conn = ldap3.Connection(server, auto_bind=True)

def _clean_ldap_attrs(entry, objectClass):
    term_dict = entry.entry_attributes_as_dict
    collect_attrs = university_json["calendar"][objectClass]
    clean_attrs = {}
    for key in collect_attrs:
        clean_attrs[key] = term_dict[key] if key in term_dict else None
    return clean_attrs

def get_ongoing_terms():
    logging.debug("Searching for active terms...")
    ldap_conn.search(SEARCH_PREFIX, '(objectClass=uOfATerm)',
                    attributes=ldap3.ALL_ATTRIBUTES, paged_size=50000)
    terms = ldap_conn.entries
    curr_terms = []
    today_date = datetime.datetime.now()
    for term in terms:
        clean_term = _clean_ldap_attrs(term, "uOfATerm")
        term_end_str = clean_term["endDate"][0]
        term_end_date = datetime.datetime.strptime(term_end_str, '%Y-%m-%d')
        if term_end_date < today_date:
            continue
        curr_terms.append(clean_term)
    return curr_terms

def _create_table(sqlcursor, table_name, attrs):
    cols = ' text, '.join(attrs) + ' text'
    query = f"CREATE TABLE IF NOT EXISTS {table_name}({cols})" 
    sqlcursor.execute(query)

def _write_entry(sqlcursor, table, attrs):
    var_holders = ', '.join(['?' for _ in range(len(attrs))])
    values = [tuple([str(attr[0]) if attr else None for attr in attrs.values()])]
    query = f"INSERT INTO {table} VALUES({var_holders})"
    if table == 'uOfAClass':
        print(values[0][5])
    sqlcursor.executemany(query, values)

def make_db(term_code:str, term_db_path:str):
    logging.debug(f"Adding data for term {term_code}...")
    sqlconn = sqlite3.connect(term_db_path)
    sqlcursor = sqlconn.cursor()
    for objectClass in university_json["calendar"]:
        _create_table(sqlcursor, objectClass, university_json["calendar"][objectClass])
        ldap_conn.search(f"term={term_code},{SEARCH_PREFIX}", f"(objectClass={objectClass})",
                    attributes=ldap3.ALL_ATTRIBUTES, paged_size=50000)
        for object in ldap_conn.entries:
            attrs = _clean_ldap_attrs(object, objectClass)
            _write_entry(sqlcursor, objectClass, attrs)
    sqlconn.commit()
    sqlconn.close()

def UID_to_name(sqlcursor, UID):
    name_query = "SELECT Name FROM uOfANames WHERE instructorUid=?"
    sqlcursor.execute(name_query, (str(UID),))
    name = sqlcursor.fetchone()
    if not name:
        logging.debug(f"{UID} not cached, scraping name...")
        url = f"https://apps.ualberta.ca/directory/person/{UID}"
        soup = BeautifulSoup(requests.get(url).text, "lxml")
        name = str(UID)
        try:
            name = soup.find("h2", {"class": "card-title mb-2"}).text
            name, *_ = name.partition(',')
        except:
            name = str(UID)
            logging.warn(f"Name not found for UID: {UID}")
        sqlcursor.execute("INSERT INTO uOfANames VALUES (?, ?)", (UID, name))
        logging.debug(f"Mapped {UID} -> {name}")

def make_names_table(db_path):
    logging.debug(f"Gathering instructorUid names...")
    sqlconn = sqlite3.connect(db_path)
    sqlcursor = sqlconn.cursor()
    sqlcursor.execute("CREATE TABLE IF NOT EXISTS uOfANames (instructorUid text, Name text)")
    sqlcursor.execute("SELECT instructorUid FROM uOfAClass WHERE instructorUid IS NOT NULL")
    UIDs = set()
    for entry in sqlcursor.fetchall():
        for UID in list(entry):
            if not UID in UIDs:
                UIDs.add(UID)
                UID_to_name(sqlcursor, UID)
    sqlconn.commit()
    sqlconn.close()

def cleanup(db_path):
    logging.debug("Pruning courses and classes that have no classtimes...")
    sqlconn = sqlite3.connect(db_path)
    sqlcursor = sqlconn.cursor()
    sqlcursor.execute("DELETE FROM uOfACourse WHERE course IN\
        (SELECT uOfACourse.course FROM uOfACourse LEFT JOIN uOfAClassTime\
        ON uOfACourse.course=uOfAClassTime.course AND uOfACourse.term=uOfAClassTime.term\
        WHERE uOfAClassTime.course IS NULL)")
    sqlconn.commit()
    sqlconn.close()

def fetch_all(db_path):
    for ongoing_term in get_ongoing_terms():
        term_code = str(ongoing_term["term"][0])
        make_db(term_code, db_path)
    cleanup(db_path)
    make_names_table(db_path)

def db_update():
    tmp_db_path = os.path.join(dirname, "../local/tmp.db")
    tmp_db_exists = os.path.exists(tmp_db_path)
    if tmp_db_exists:
        os.remove(tmp_db_path)
        logging.debug("Existing temp database deleted.")
    tmp_db_conn = sqlite3.connect(tmp_db_path)
    tmp_db_cursor = tmp_db_conn.cursor()
    old_db_path = os.path.join(dirname, "../local/database.db")
    old_db_exists = os.path.exists(old_db_path)
    if old_db_exists:
        logging.debug("Old database exists, copying over the names table.")
        old_db_conn = sqlite3.connect(old_db_path)
        old_db_cursor = old_db_conn.cursor()
        tmp_db_cursor.execute("CREATE TABLE IF NOT EXISTS uOfANames (instructorUid text, Name text)")
        old_db_cursor.execute("SELECT * FROM uOfANames")
        for UID, name in old_db_cursor.fetchall():
            tmp_db_cursor.execute("INSERT INTO uOfANames VALUES (?, ?)", (UID, name))
        tmp_db_conn.commit()
        tmp_db_conn.close()
        old_db_conn.close()
        logging.debug("Copied new names over.")
    fetch_all(tmp_db_path)
    if old_db_exists:
        os.remove(old_db_path)
        logging.debug("Old database deleted.")
    os.rename(tmp_db_path, old_db_path)
    logging.debug("Updated database")

db_update()
