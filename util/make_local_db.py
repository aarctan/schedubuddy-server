import json
import ldap3
import sqlite3
import logging
import sys
import os
import datetime
import shutil
import requests
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
        if term_end_date < today_date or "Continuing" in clean_term["termTitle"][0]:
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
    sqlcursor.executemany(query, values)

def make_local_db(term_code:str, term_db_path:str):
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

def searchUIDforName(id):
    url = f"https://apps.ualberta.ca/directory/person/{id}"
    soup = BeautifulSoup(requests.get(url).text, "lxml")
    name = str(id)
    try:
        name = soup.find("h2", {"class": "card-title mb-2"}).text
        name, *_ = name.partition(',')
    except:
        name = str(id)
        print(f"Name not found for UID: {id}")
    return name

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
                name = searchUIDforName(UID)
                sqlcursor.execute("INSERT INTO uOfANames VALUES (?, ?)", (UID, name))
    sqlconn.commit()
    sqlconn.close()

def cleanup(db_path):
    logging.debug("Pruning courses that have no classtimes...")
    sqlconn = sqlite3.connect(db_path)
    sqlcursor = sqlconn.cursor()
    sqlcursor.execute("DELETE FROM uOfACourse WHERE course IN\
        (SELECT uOfACourse.course FROM uOfACourse LEFT JOIN uOfAClassTime\
        ON uOfACourse.course=uOfAClassTime.course AND uOfACourse.term=uOfAClassTime.term\
        WHERE uOfAClassTime.course IS NULL)")
    sqlcursor.execute("DELETE FROM uOfAClass WHERE class IN\
        (SELECT uOfAClass.class FROM uOfAClass LEFT JOIN uOfAClassTime\
        ON uOfAClass.class=uOfAClassTime.class AND uOfAClass.term=uOfAClassTime.term\
        AND uOfAClass.course=uOfAClassTime.course\
        WHERE uOfAClassTime.class IS NULL)")
    sqlconn.commit()
    sqlconn.close()

def fetch_all(flush=True):
    try:
        os.mkdir("local")
    except:
        pass
    logging.debug("Created local database directory.")
    term_db_path = os.path.join(dirname, "../local/database.db")
    if not os.path.exists(term_db_path):
        for ongoing_term in get_ongoing_terms():
            term_code = str(ongoing_term["term"][0])
            make_local_db(term_code, term_db_path)
    make_names_table(term_db_path)
    cleanup(term_db_path)

#term_db_path = os.path.join(dirname, "../local/database.db")
#cleanup(term_db_path)