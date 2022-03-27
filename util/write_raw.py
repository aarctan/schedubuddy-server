import json
import logging
import os
import re
import requests
import time

from bs4 import BeautifulSoup

ROOT_URL = "https://apps.ualberta.ca/catalogue"
CATALOG_H2_CLASS = "flex-grow-1"
TERM_DIV_CLASS = "card mt-4"
TERM_H4_CLASS = "m-0 flex-grow-1"
COMPONENT_DIV_CLASS = "col-12"
COMPONENT_H3_CLASS = "mt-2 d-none d-md-block"
CLASS_DIV_CLASS = "col-lg-4 col-12 pb-3"
CLASS_STRONG_CLASS = "mb-0 mt-4"


# Returns a list of codes from a list on a webpage (i.e., faculty or subject codes)
def get_link_codes_with_prefix(url, prefix):
    soup = BeautifulSoup(requests.get(url).text, "lxml")
    soups = soup.findAll("a")
    codes = []
    for soup in soups:
        if soup.has_attr("href"):
            link = soup["href"]
            if link[: len(prefix)] == prefix:
                code = link[len(prefix) + 1 :].upper()
                if not code:
                    continue
                codes.append(code)
    return codes


logger = logging.basicConfig()


def get_faculties_from_catalogue():
    return get_link_codes_with_prefix(f"{ROOT_URL}", "/catalogue/faculty")


def get_subjects_from_faculty(faculty_code):
    return get_link_codes_with_prefix(f"{ROOT_URL}/faculty/{faculty_code}", "/catalogue/course")


# Returns a list of catalogs from a subject, e.g. "CMPUT" -> ['101', '174', ...]
def get_catalogs_from_subject(subject):
    courses_soup = BeautifulSoup(requests.get(f"{ROOT_URL}/course/{subject}").text, "lxml")
    course_titles = courses_soup.select("h2", {"class": CATALOG_H2_CLASS})
    catalogs = []
    for course_title in course_titles:
        catalog = course_title.text.lstrip()[len(subject) + 1 :].split(" ")[0]
        if re.match(r"\d{3,}[A-Z]?", catalog, re.IGNORECASE):
            catalogs.append(catalog)
        else:
            # todo: warn we found an element, but failed verify that it's a course number?
            pass
    return catalogs


def write_raw(subject, catalog, fp):
    def process_raw_class_str(raw_class_str):
        raw = raw_class_str.lstrip().rstrip().split(" ")
        lec, section, class_id = raw[0][:3].upper(), raw[1], raw[2]
        id_cutoff = class_id.find("\n")
        class_id = class_id[1 : (id_cutoff - 1 if id_cutoff != -1 else -1)]
        return lec, section, class_id

    class_objs = []
    course_url = f"{ROOT_URL}/course/{subject}/{catalog}"
    classes_soup = BeautifulSoup(requests.get(course_url).text, "lxml")
    soup_divs = classes_soup.findAll("div", {"class": TERM_DIV_CLASS})
    for soup_div in soup_divs:
        term_header = soup_div.find("h4", {"class": TERM_H4_CLASS})
        term_name, term_id = term_header.text, term_header["id"]
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
                raw_class_str = raw_class_str.replace("\n", " ").lstrip().rstrip()
                class_body = class_soup.findAll("em")
                embeds = [str(body.text).lstrip().rstrip() for body in class_body]
                write_obj = {
                    "term": term_id,
                    "termName": term_name,
                    "subject": subject,
                    "header": raw_class_str,
                    "catalog": catalog,
                    "section": section,
                    "classId": class_id,
                    "component": component_type,
                    "embeds": embeds,
                }
                class_objs.append(write_obj)
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
    if debug:
        subjects = ["CHEM"]
    else:
        faculty_codes = get_faculties_from_catalogue()  # ['ED', 'EN', 'SC', ...]
        subjects = []
        for faculty_code in faculty_codes:
            subjects += get_subjects_from_faculty(faculty_code)
        subjects = list(set(subjects))  # ['CHEM, 'CMPUT', 'MATH', ...]
    raw_data = []
    for subject in subjects:
        course_nums = set(get_catalogs_from_subject(subject))  # ['101', '174', ...]
        print(course_nums)
        for course_num in course_nums:
            raw_objs = write_raw(subject, course_num, raw_file)
            for raw_obj in raw_objs:
                raw_data.append(raw_obj)
            print(f"Read {subject} {course_num}")
        time.sleep(1)
    raw_file.write(json.dumps(raw_data, sort_keys=True, indent=4))
    raw_file.close()


if __name__ == "__main__":
    main()
