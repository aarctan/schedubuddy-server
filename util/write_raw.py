import argparse
import concurrent.futures
from concurrent import futures
from datetime import datetime
from pathlib import Path

import dateutil.parser as dparser
import re, requests, os, json, time
from bs4 import BeautifulSoup

ROOT = "https://apps.ualberta.ca/catalogue"
TERM_DIV_CLASS = "mb-5"
COMPONENT_DIV_CLASS = "col-12"
COMPONENT_H3_CLASS = "mt-2 d-none d-md-block"
CLASS_DIV_CLASS = "col-lg-4 col-12 pb-3"
CLASS_STRONG_CLASS = "mb-0 mt-4"


# Returns a list of codes from a list on a webpage (i.e., faculty or subject codes)
def get_link_codes_with_prefix(url: str, prefix: str):
    soup = BeautifulSoup(requests.get(url).content, "lxml")
    soups = soup.select("a[href]")
    codes = []
    for soup in soups:
        link = soup["href"]
        if link[:len(prefix)] == prefix:
            code = link[len(prefix) + 1:].upper()
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
    courses_soup = BeautifulSoup(requests.get(f"{ROOT}/course/{subject}").content, "lxml")
    # "first" class selects the first course of the card
    # there are sometimes multiple items for card if the course is changing in the future
    course_titles = courses_soup.select(".course.first h2 > a")
    catalogs = []
    for course_title in course_titles:
        try:
            # eg matches 331 in "AN TR 331". asserts the subject prefixes the course number
            pattern = re.escape(subject.replace("_", " ")) + r" (\d{1,4}\w{1,3})"
            catalogs.append(re.search(pattern, course_title.text).group(1))
        except AttributeError as e:
            raise AttributeError(f"Failed to parse course title {course_title.text=}. "
                                 f"Is the selector grabbing the wrong elements? {e=}")
    return catalogs


def write_raw(subject, course_num):
    print(f"Reading {subject} {course_num}")
    class_objs = []
    course_url = f"{ROOT}/course/{subject}/{course_num}"
    classes_soup = BeautifulSoup(requests.get(course_url).content, "lxml")
    soup_divs = classes_soup.findAll("div", {"class": TERM_DIV_CLASS})
    for soup_div in soup_divs:
        term_header = soup_div.find("h2")
        term_name, term_id = term_header.text.replace('\n', '').strip(), term_header['id']
        num_conts = len(soup_div.findAll("h3"))
        children = soup_div.findChildren(recursive=False)
        # Workaround to skip "This course is changing in this term...":
        # Seek to the first <h3> and truncate all earlier children
        currChild = 0
        while children[currChild].name != "h3":
            currChild += 1
        children = children[currChild:]
        for i in range(num_conts):
            component_type = children[i * 2].text[:3].upper()
            component_table = children[i * 2 + 1]
            table_body = component_table.find("tbody")
            table_rows = table_body.find_all("tr")
            for tr in table_rows:
                tr_Section = tr.find("td", {"data-card-title": "Section"})
                tr_DTL = tr.find("td", {"data-card-title": "Dates + Times + Locations"})
                tr_Instructors = tr.find("td", {"data-card-title": "Instructor(s)"})
                # Section
                raw_section = tr_Section.text.replace('\n', '').strip().split(' ')
                component, section, class_id = raw_section[0], raw_section[1], raw_section[-1]
                class_id = class_id[1:-1] # remove brackets
                # Class times
                div_root = tr_DTL.find("div", {"class": "row row-cols-1 row-cols-lg-3"})
                divs = div_root.find_all("div", {"class": "col"})
                num_rows = len(divs) // 3
                cts = []
                for i in range(num_rows):
                    dates, times, loc = divs[i*3], divs[i*3 + 1], divs[i*3 + 2]
                    ct = (dates.text.strip(), times.text.strip(), loc.text.strip())
                    cts.append(ct)
                # Instructors
                instructor = None
                instructor_soup = tr_Instructors.find("a")
                if instructor_soup:
                    instructor = instructor_soup.text.strip()

                raw_obj = {
                    "catalog":course_num,
                    "classId": class_id,
                    "component": component,
                    "section": section,
                    "instructor": instructor,
                    "classTimes": cts,
                    "subject": subject,
                    "term": term_id,
                    "termName": term_name
                }
                class_objs.append(raw_obj)
    return class_objs


def main():
    parser = argparse.ArgumentParser(description="write_raw", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--max-workers", type=int, default=3, help="Number of maximum workers to use")
    parser.add_argument("--debug", action="store_true", help="Enable debugging mode.")
    args = parser.parse_args()
    debug = args.debug

    root = Path(__file__).parent.parent
    raw_file_path = root / "local/raw.json"
    if raw_file_path.exists():
        os.remove(raw_file_path)
    raw_file = open(raw_file_path, "a")
    subjects = []
    # disable debug mode
    print(f"starting at {datetime.now()}")
    start = time.perf_counter()
    if debug:
        subjects = ['CHEM']
    else:
        print(f"Reading faculties from course_num...")
        faculty_codes = sorted(get_faculties_from_catalogue())  # ['ED', 'EN', 'SC', ...]
        print(f"Read {len(faculty_codes)} faculties from course_num.\n")
        print(f"Reading subjects from faculties...")
        subjects = set()
        for faculty_code in faculty_codes:
            subjects.update(get_subjects_from_faculty(faculty_code))
        subjects = sorted(subjects)  # ['CHEM, 'CMPUT', 'MATH', ...]
    print(f"Read {len(subjects)} subjects.")

    raw_data = []
    failures = []
    for i, subject in enumerate(subjects):
        print(f"Reading {subject} ({i + 1}/{len(subjects)})...")
        if debug:
            course_nums = ['101']
        else:
            course_nums = set(get_catalogs_from_subject(subject))  # ['101', '174', ...]

        print(f"Reading {len(course_nums)} course{'s' if len(course_nums) != 1 else ''} in {subject}...")
        subject_buffer = []
        with futures.ThreadPoolExecutor(max_workers=args.max_workers) as exe:
            write_raw_subject = lambda c_num: write_raw(subject, c_num)
            fut_to_c_num = {exe.submit(write_raw_subject, course_n): course_n for course_n in course_nums}
            # results will come in as they're completed, we need to sort this after the fact
            for fut in concurrent.futures.as_completed(fut_to_c_num):
                try:
                    subject_buffer.extend(fut.result())
                except Exception as e:
                    course_num = fut_to_c_num[fut]
                    failures.append(f"{subject} {course_num}: {e}")
        # sort by course num, then term no, then section, then class id. just allows for easier diffs if necessary
        subject_buffer.sort(key=lambda x: (x["catalog"], x["term"], x["section"], x["classId"]))
        raw_data.extend(subject_buffer)
        print(f"Done reading {subject}.\n")
        print(f"Failures: {failures}")
    raw_file.write(json.dumps(raw_data, sort_keys=True, indent=4))
    raw_file.close()
    print(f"finished in {time.perf_counter() - start:.1f}s")


main()
