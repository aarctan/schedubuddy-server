from multiprocessing import Pool, Process, Manager, cpu_count
import sqlite3, os, requests
from dateutil.parser import parse
from bs4 import BeautifulSoup

ROOT = "https://apps.ualberta.ca/catalogue"
CATALOG_H4_CLASS = "flex-grow-1"
TERM_DIV_CLASS = "card mt-4 dv-card-flat"
TERM_H4_CLASS = "m-0 flex-grow-1"
COMPONENT_DIV_CLASS = "col-12"
COMPONENT_H3_CLASS = "mt-2 d-none d-md-block"
CLASS_DIV_CLASS = "col-lg-4 col-12 pb-3"
CLASS_STRONG_CLASS = "mb-0 mt-4"

term_title_to_start_date = {}
dirname = os.path.dirname(__file__)
db_path = os.path.join(dirname, "../local/database.db")
db_conn = sqlite3.connect(db_path)
db_cursor =  db_conn.cursor()
db_cursor.execute("SELECT termTitle, startDate FROM uOfATerm")
for term_title, start_date in  db_cursor.fetchall():
    term_title_to_start_date[term_title] = parse(start_date)
subject_biweekly_tuples = {}

def is_date(string):
    try: 
        parse(string, fuzzy=False)
        return True
    except ValueError:
        return False

def commit_biweekly_to_db(cursor, tuples):
    for class_id, biweekly_flag in tuples:
        query = "UPDATE uOfAClassTime SET biweekly=? WHERE class=?"
        cursor.execute(query, (biweekly_flag, class_id))

def process_raw_class_str(raw_class_str):
    raw_class_arr = raw_class_str.lstrip().rstrip().split(' ')
    lec = raw_class_arr[0][:3].upper()
    section = raw_class_arr[1]
    class_id = raw_class_arr[2]
    id_cutoff = class_id.find('\n')
    class_id = class_id[1:(id_cutoff-1 if id_cutoff != -1 else -1)]
    return lec, section, class_id

def is_biweekly(class_body, term_start_date):
    time_tags = []
    for tag in class_body:
        if not "-" in tag.text:
            continue
        time_tags.append(tag.text.lstrip().rstrip().split('\n'))
    # Check the first time tag. If it has form "YYYY-MM-DD HH:MM - HH:MM" then
    # check that every tag has the same form with the same HH:MM - HH:MM.
    first_time_tag = time_tags[0]
    biweekly = False
    if len(first_time_tag) == 1 and ':' in first_time_tag[0]:
        date1, start_t1, end_t1 = first_time_tag[0].replace('- ', '').split(' ')[:3]
        for time_tag in time_tags:
            if len(time_tag) != 1 or not ':' in time_tag[0]:
                break
            date, start_t, end_t = time_tag[0].replace('- ', '').split(' ')[:3]
            if start_t != start_t1 or end_t != end_t1:
                break
            if (parse(date) - parse(date1)).days == 14:
                biweekly = True
            date1 = date
    if biweekly:
        date1 = first_time_tag[0].replace('- ', '').split(' ')[0]
        delta = (parse(date1) - term_start_date).days
        return 1 if delta < 13 else 2
    return 0

def get_biweekly_classes(subject, catalog, title_to_start_date):
    course_url = f"{ROOT}/course/{subject}/{catalog}"
    classes_soup = BeautifulSoup(requests.get(course_url).text, "lxml")
    soup_divs = classes_soup.findAll("div", {"class": TERM_DIV_CLASS})
    biweekly_tuples = []
    for soup_div in soup_divs:
        term_name = soup_div.find("h4", {"class": TERM_H4_CLASS}).text
        if term_name not in title_to_start_date:
            continue
        term_start_date = title_to_start_date[term_name]
        soup_components = soup_div.findAll("div", {"class": COMPONENT_DIV_CLASS})
        for soup_component in soup_components:
            component_type = soup_component.find("h3", {"class": COMPONENT_H3_CLASS})
            if not component_type:
                continue
            component_type = component_type.text[:3].upper()
            class_soups = soup_component.findAll("div", {"class": CLASS_DIV_CLASS})
            for class_soup in class_soups:
                raw_class_str = class_soup.find("strong", {"class": CLASS_STRONG_CLASS}).text
                _, section, class_id = process_raw_class_str(raw_class_str)
                class_body = class_soup.findAll("em")
                biweekly_flag = is_biweekly(class_body, term_start_date)
                if biweekly_flag > 0:
                    biweekly_tuples.append((class_id, biweekly_flag))
    return biweekly_tuples

# Returns a list of catalogs from a subject, e.g. "CMPUT" -> ['101', '174', ...]
def get_catalogs_from_subject(subject):
    courses_soup = BeautifulSoup(requests.get(f"{ROOT}/course/{subject}").text, "lxml")
    course_titles = courses_soup.findAll("h4", {"class": CATALOG_H4_CLASS})
    catalogs = []
    for course_title in course_titles:
        catalog = course_title.text.lstrip()[len(subject)+1:].split(' ')[0]
        catalogs.append(catalog)
    return catalogs

# Returns a list of codes from a list on a webpage (i.e., faculty or subject codes)
def get_link_codes_with_prefix(url, prefix):
    soup = BeautifulSoup(requests.get(url).text, "lxml")
    soups = soup.findAll("a")
    codes = []
    for soup in soups:
        if soup.has_attr("href"):
            link = soup["href"]
            if link[:len(prefix)] == prefix:
                code = link[len(prefix)+1:].upper()
                if not code:
                    continue
                codes.append(code)
    return codes

# Returns a list of subjects from a faculty, e.g. "SC" -> ['ASTRO', 'BIOIN', ...]
# Note that some subjects can be repeated across faculties. For example, PSYCO
# belongs to faculties AR and SC. Duplicates should be removed.
def get_subjects_from_faculty(faculty_code):
    return get_link_codes_with_prefix(
        f"{ROOT}/faculty/{faculty_code}",
        "/catalogue/course")

# Returns a list of faculties, e.g. ['AH', 'AR', 'AU', 'BC', 'ED', 'EN', ...]
def get_faculties_from_catalogue():
    return get_link_codes_with_prefix(
        f"{ROOT}",
        "/catalogue/faculty")

def scrape(d, subject):
    tuples = []
    for catalog in get_catalogs_from_subject(subject):
        try:
            biweekly_tuples =\
                get_biweekly_classes(subject, catalog, term_title_to_start_date)
            if len(biweekly_tuples) > 0:
                print(f"Found {len(biweekly_tuples)} biweekly classes for {subject} {catalog}")
                tuples += biweekly_tuples
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Errored on {subject} {catalog}")
            print(e)
    d[subject] = tuples

# https://stackoverflow.com/questions/434287
def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

if __name__ == "__main__":
    faculty_codes = get_faculties_from_catalogue()
    all_subjects = []
    for faculty_code in faculty_codes:
        all_subjects += get_subjects_from_faculty(faculty_code)
    all_subjects = list(set(all_subjects))
    manager = Manager()
    d = manager.dict()
    simul_processes = cpu_count()-1 or 1
    for chunk in chunker(all_subjects, 4):
        job = [Process(target=scrape, args=(d, subject)) for subject in chunk]
        _ = [p.start() for p in job]
        _ = [p.join() for p in job]
    for biweekly_tuples in d.values():
        commit_biweekly_to_db(db_cursor, biweekly_tuples)
    db_conn.commit()
    db_conn.close()