import json, ldap3, sqlite3, logging, sys, os, datetime, shutil

# Set logging level to at least INFO to disable debug messages.
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

university_json_f = open("uAlberta.json")
university_json = json.load(university_json_f)
university_json_f.close()

SEARCH_PREFIX = "ou=calendar,dc=ualberta,dc=ca"
server = ldap3.Server(university_json["server"])
ldap_conn = ldap3.Connection(server, auto_bind=True)

def get_ongoing_terms():
    logging.debug("Searching for active terms...")
    ldap_conn.search(SEARCH_PREFIX, '(objectClass=uOfATerm)', attributes=ldap3.ALL_ATTRIBUTES)
    terms = ldap_conn.entries
    curr_terms = []
    today_date = date_time_obj = datetime.datetime.now()
    for term in terms:
        term_dict = term.entry_attributes_as_dict
        collect_attrs = university_json["calendar"]["uOfATerm"]
        key_intersect = term_dict.keys() & collect_attrs
        clean_term = {}
        for key in key_intersect:
            clean_term[key] = term_dict[key]
        if "Continuing" in clean_term["termTitle"][0]:
            continue
        term_end_str = clean_term["endDate"][0]
        term_end_date = datetime.datetime.strptime(term_end_str, '%Y-%m-%d')
        if term_end_date > today_date:
            curr_terms.append(clean_term)
    return curr_terms

def _clean_ldap_attrs(entry, objectClass):
    term_dict = entry.entry_attributes_as_dict
    collect_attrs = university_json["calendar"][objectClass]
    clean_attrs = {}
    for key in collect_attrs:
        clean_attrs[key] = term_dict[key] if key in term_dict else None
    return clean_attrs

def _create_table(sqlcursor, table_name, attrs):
    cols = ' text, '.join(attrs) + ' text'
    query = f"CREATE TABLE IF NOT EXISTS {table_name}({cols})" 
    sqlcursor.execute(query)

def _write_entry(sqlcursor, table, attrs):
    var_holders = ', '.join(['?' for _ in range(len(attrs))])
    values = [tuple([str(attr[0]) if attr else None for attr in attrs.values()])]
    query = f"INSERT INTO {table} VALUES({var_holders})"
    sqlcursor.executemany(query, values)

def make_local_db(term_code:str, term_db_path:str):
    sqlconn = sqlite3.connect(term_db_path)
    sqlcursor = sqlconn.cursor()
    prefix = f"term={term_code},{SEARCH_PREFIX}"
    ldap_conn.search(prefix, '(objectClass=uOfACourse)', attributes=ldap3.ALL_ATTRIBUTES, paged_size=50000)
    uOfACourses = ldap_conn.entries
    _create_table(sqlcursor, "uOfACourse", university_json["calendar"]["uOfACourse"])
    for uOfACourse in uOfACourses:
        attrs = _clean_ldap_attrs(uOfACourse, "uOfACourse")
        _write_entry(sqlcursor, "uOfACourse", attrs)
    sqlconn.commit()
    sqlconn.close()
    
def fetch_all(flush=False):
    if flush:
        shutil.rmtree("../local")
        logging.warning("All local databases were flushed.")
    if not os.path.exists("../local"):
        os.mkdir("../local")
        logging.debug("Created local database directory.")
    for ongoing_term in get_ongoing_terms():
        term_code = str(ongoing_term["term"][0])
        dirname = os.path.dirname(__file__)
        term_db_path = os.path.join(dirname, "../local/"+term_code+".db")
        if not os.path.exists(term_db_path):
            make_local_db(term_code, term_db_path)

fetch_all(flush=True)
