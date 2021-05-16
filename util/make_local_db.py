import json, ldap3, sqlite3, logging, sys, os, datetime

# Set logging level to at least INFO to disable debug messages.
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

university_json_f = open("uAlberta.json")
university_json = json.load(university_json_f)
university_json_f.close()

server = ldap3.Server(university_json["server"])
ldap_conn = ldap3.Connection(server, auto_bind=True)

logging.debug("Searching for active terms...")
SEARCH_PREFIX = "ou=calendar,dc=ualberta,dc=ca"
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
    term_end_str = clean_term["endDate"][0]
    term_end_date = datetime.datetime.strptime(term_end_str, '%Y-%m-%d')
    if term_end_date > today_date:
        curr_terms.append(clean_term)

for a in curr_terms:
    print(a)
