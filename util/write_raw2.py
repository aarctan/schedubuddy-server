import json
import logging
import re
import time
from pathlib import Path
from typing import Set

import requests
from lxml import html
from requests.adapters import HTTPAdapter, Retry

logging.basicConfig(format="{asctime} {levelname}:{lineno} {message}", style="{")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ROOT_COURSE_DIR_URL = "https://apps.ualberta.ca/catalogue"
KNOWN_COMPONENT_TYPES = {
    "LEC",  # lecture
    "SEM",  # seminar
    "LAB",
    "CLI",  # clinical
    "THE",  # thesis
}

s = requests.Session()

# occasionally, connection will get reset on us
# retry w/ backoff if that happens
retries = Retry(total=5,
                backoff_factor=0.1,
                status_forcelist=[500, 502, 503, 504])

s.mount('http://', HTTPAdapter(max_retries=retries))
s.mount('https://', HTTPAdapter(max_retries=retries))

def get_faculties_from_catalogue() -> Set[str]:
    return get_link_codes_with_prefix(f"{ROOT_COURSE_DIR_URL}", "/catalogue/faculty/")


def get_subjects_from_faculty(faculty_code: str) -> Set[str]:
    return get_link_codes_with_prefix(f"{ROOT_COURSE_DIR_URL}/faculty/{faculty_code}", "/catalogue/course/")


def get_link_codes_with_prefix(url: str, href_prefix: str) -> Set[str]:
    parsed = html.fromstring(s.get(url).content)
    codes = set()
    for a_elem in parsed.cssselect(f"a[href^=\"{href_prefix}\"]"):
        code = a_elem.get("href").replace(href_prefix, "")
        if len(code) > 0:
            codes.add(code.upper())
    return codes


def get_catalogs_from_subject(subject: str) -> Set[str]:
    """Returns a list of catalogs from a subject, e.g. "CMPUT" -> ['101', '174', ...]"""
    return get_link_codes_with_prefix(f"{ROOT_COURSE_DIR_URL}/course/{subject}/",
                                      f"/catalogue/course/{subject.lower()}/")


def get_class_info(subject: str, catalogNum: str):
    def process_raw_class_str(raw_class_str):
        raw = raw_class_str.lstrip().rstrip().split(" ")
        lec, section, class_id = raw[0][:3].upper(), raw[1], raw[2]
        id_cutoff = class_id.find("\n")
        class_id = class_id[1: (id_cutoff - 1 if id_cutoff != -1 else -1)]
        return lec, section, class_id

    class_objs = []
    course_url = f"{ROOT_COURSE_DIR_URL}/course/{subject}/{catalogNum}"
    parsed_class_page = html.fromstring(s.get(course_url).content)
    class_base = {
        "catalog": catalogNum,
        "subject": subject,
    }


    for term_div in parsed_class_page.cssselect(".content .container .card"):
        term_header = term_div.cssselect(".card-header")[0]
        class_component_base = {
            **class_base,
            "term": term_header.get("id"),
            "termName": term_header.text_content(),
        }

        # lab, lecture, etc
        for component in term_div.cssselect(".card-body > *"):
            if component.tag == "h3":
                class_component_base["component"] = component.text_content().upper()[:3]
                assert class_component_base["component"] in KNOWN_COMPONENT_TYPES
                continue

            for row in component.cssselect("tbody > tr"):
                cols = row.cssselect("td > span")
                section_code_search = re.search(r"(LECTURE|SEMINAR|LAB|CLINICAL|THESIS)\s+(\w+)\s+\((\d+)\)", cols[0].text_content(), re.IGNORECASE)
                class_objs.append({
                    **class_component_base,
                    # note: re groups 1 based indexing
                    "section": section_code_search.group(2),
                    "classId": section_code_search.group(3),
                    "embeds": [re.sub(r"\s{2,}", " ", x.text_content()) for x in cols[1:]]
                })

    return class_objs


def main():

    faculty_codes = get_faculties_from_catalogue()  # ['ED', 'EN', 'SC', ...]
    logger.info("retrieving faculty info")

    subjects = set()
    for faculty_code in faculty_codes:
        subjects.update(get_subjects_from_faculty(faculty_code))

    course_data = []
    for subject in subjects:
        course_nums = get_catalogs_from_subject(subject)  # ['101', '174', ...]
        logger.info(f"processing {len(course_nums)} courses in {subject}")
        for num in course_nums:
            scheduling = get_class_info(subject, num)
            logger.debug(f"found {len(scheduling)} term schedules for {subject} {num}")
            course_data.extend(scheduling)

    raw_file_output = Path(__file__).parents[1] / "local" / "raw.json"
    logger.info(f"writing {len(course_data)} courses schedules to {raw_file_output}")
    with open(raw_file_output, mode="w") as out:
        json.dump(course_data, out, sort_keys=True, indent=4)


if __name__ == '__main__':
    main()
