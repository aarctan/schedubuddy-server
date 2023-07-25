import dateutil.parser as dparser
import re, requests, os, json, time
from bs4 import BeautifulSoup

ROOT = "https://apps.ualberta.ca/catalogue"
CATALOG_H2_CLASS = "[ fs-4 ][ flex-grow-1 ][ d-flex flex-column flex-md-row gap-2 ][ align-items-start align-items-md-center ]"
TERM_DIV_CLASS = "card"
TERM_H2_CLASS = "card-header"
COMPONENT_DIV_CLASS = "col-12"
COMPONENT_H3_CLASS = "mt-2 d-none d-md-block"
CLASS_DIV_CLASS = "col-lg-4 col-12 pb-3"
CLASS_STRONG_CLASS = "mb-0 mt-4"

# Returns a list of codes from a list on a webpage (i.e., faculty or subject codes)
def get_link_codes_with_prefix(url, prefix):
    soup = BeautifulSoup(requests.get(url).content, "lxml")
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

def get_faculties_from_catalogue():
    return get_link_codes_with_prefix(
        f"{ROOT}",
        "/catalogue/faculty")

def get_subjects_from_faculty(faculty_code):
    return get_link_codes_with_prefix(
        f"{ROOT}/faculty/{faculty_code}",
        "/catalogue/course")

# Returns a list of catalogs from a subject, e.g. "CMPUT" -> ['101', '174', ...]
def get_catalogs_from_subject(subject):
    subject = "ZOOLE"
    courses_soup = BeautifulSoup(requests.get(f"{ROOT}/course/{subject}").content, "lxml")
    course_titles = courses_soup.findAll("h2", {"class": CATALOG_H2_CLASS})
    catalogs = []
    for course_title in course_titles:
        catalog = course_title.text.lstrip()[len(subject)+1:].split(' ')[0]
        catalogs.append(catalog)
    return catalogs

def write_raw(subject, catalog, fp):
    class_objs = []
    course_url = f"{ROOT}/course/{subject}/{catalog}"
    classes_soup = BeautifulSoup(requests.get(course_url).content, "lxml")
    soup_divs = classes_soup.findAll("div", {"class": TERM_DIV_CLASS})
    for soup_div in soup_divs:
        term_header = soup_div.find("h2", {"class": TERM_H2_CLASS})
        term_name, term_id = term_header.text, term_header['id']
        cont_soup = soup_div.find("div", {"class": "card-body"})
        num_conts = len(cont_soup.findAll("h3"))
        children = cont_soup.findChildren(recursive=False)
        # Workaround to skip "This course is changing in this term...":
        # Seek to the first <h3> and truncate all earlier children
        currChild = 0
        while children[currChild].name != "h3":
            currChild += 1
        children = children[currChild:]
        for i in range(num_conts):
            component_type = children[i*2].text[:3].upper()
            component_table = children[i*2+1]
            headers = component_table.find_all('th')
            rows = {}
            for header in headers:
                header_name = header.text.strip()
                if header_name == "Capacity":
                    continue
                rows[header_name] = []
                row_soup = component_table.find_all("td", {"data-card-title": header_name})
                row_count = len(row_soup)
                for row in row_soup:
                    col = row.find("div") # CONTENT
                    if not col:
                        rows[header_name].append(None)
                        continue
                    raw_candidate = col.text.strip()
                    rows[header_name].append(raw_candidate)
            rows = list(rows.values())
            for row_itr in range(row_count):
                class_id, section, embeds = None, None, None
                embeds = ["Capacity: 0"] # Do not use capacity, need column for compatibility with old db schema
                candidate_row = [rows[i][row_itr] for i in range(3)]
                for raw_candidate in candidate_row:
                    # col Section for class section and class id
                    #print(raw_candidate)
                    if component_type in raw_candidate:
                        clean_raw_cand = list(filter(('').__ne__, raw_candidate.split(' ')))
                        has_syllabus = clean_raw_cand[-1].strip().lower() == "syllabus"
                        section = clean_raw_cand[1].strip()
                        class_id = clean_raw_cand[-4][1:-2] if has_syllabus else clean_raw_cand[2][1:-1]
                    # col Instructor(s); only deal with primary instructor
                    elif "Primary Instructor: " in raw_candidate:
                        instructor_name = raw_candidate[len("Primary Instructor: ")+1:]
                        embeds.append(f"Primary Instructor: {instructor_name}")
                    # col for Dates + Times (embed)
                    elif re.search('\d+-\d+-\d+ \d+:\d+ - \d+:\d+', raw_candidate):
                        for class_instance in [i.strip() for i in raw_candidate.split('\n')]:
                            if class_instance == '':
                                continue
                            embeds.append(class_instance)
                    elif re.search('\d+-\d+-\d+ - \d+-\d+-\d+', raw_candidate):
                        clean_str = '\n'.join([i.strip() for i in raw_candidate.strip().split('\n') if i.strip() != ''])
                        embeds.append(clean_str)
                raw_obj = {
                    "catalog": catalog,
                    "classId": class_id,
                    "component": component_type,
                    "embeds": embeds,
                    "section": section,
                    "subject": subject,
                    "term": term_id,
                    "termName": term_name,
                }
                class_objs.append(raw_obj)
    return class_objs

debug = False
def main():
    dirname = os.path.dirname(__file__)
    raw_file_path = os.path.join(dirname, "../local/raw.json")
    raw_file_exists = os.path.exists(raw_file_path)
    if raw_file_exists:
        os.remove(raw_file_path)
    raw_file = open(raw_file_path, "a")
    subjects = []
    # disable debug mode
    if debug:
        subjects = ['PL_SC']
    else:
        print(f"Reading faculties from catalog...")
        faculty_codes = sorted(get_faculties_from_catalogue()) # ['ED', 'EN', 'SC', ...]
        print(f"Read {len(faculty_codes)} faculties from catalog.\n")
        print(f"Reading subjects from faculties...")
        subjects = []
        for faculty_code in faculty_codes:
            subjects += get_subjects_from_faculty(faculty_code)
        subjects = sorted(set(subjects)) # ['CHEM, 'CMPUT', 'MATH', ...]
    raw_data = []
    print(f"Read {len(subjects)} subjects.\n")
    #time.sleep(3)
    failures = []
    for i, subject in enumerate(subjects):
        print(f"Reading {subject} ({i + 1}/{len(subjects)})...")
        if debug:
            course_nums = ['352']
        else:
            course_nums = set(get_catalogs_from_subject(subject)) # ['101', '174', ...]
        course_nums = sorted(course_nums)
        print(f"Reading {len(course_nums)} course{'s' if len(course_nums) != 1 else ''} in {subject}...")
        for course_num in course_nums:
            #if course_num != "330":
            #   continue
            print(f"Reading {subject} {course_num}")
            try:
                raw_objs = write_raw(subject, course_num, raw_file)
                for raw_obj in raw_objs:
                    raw_data.append(raw_obj)
            except:
                failures.append(f"{subject} {course_num}")
            #time.sleep(2.5)
        print(f"Done reading {subject}.\n")
        print(f"Failures: {failures}")
    raw_file.write(json.dumps(raw_data, sort_keys=True, indent=4))
    raw_file.close()

main()
