import argparse
import concurrent
import json
import logging
import operator
import re
import time
from concurrent import futures
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Callable, Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

logging.basicConfig(format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class Course:
    subject: str  # eg CMPUT, ENGL
    number: str  # eg 174, 205A

    def __hash__(self):
        return hash(self.number + self.subject)

    def __str__(self):
        return f"<Course {self.subject} {self.number}>"


class Scraper:
    ROOT = "https://apps.ualberta.ca/catalogue"

    def __init__(
        self,
        cache_dir: Path,
        cache_ttl_minutes: float,
        max_workers: int,
        use_processes: bool,
    ) -> None:
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_minutes = cache_ttl_minutes
        self.max_workers = max_workers
        self.concurrent_impl = (
            concurrent.futures.ProcessPoolExecutor
            if use_processes
            else concurrent.futures.ThreadPoolExecutor
        )
        self.use_processes = use_processes
        self.http_client = requests.Session()

    def _ttl_expired(self, file: Path) -> bool:
        if self.cache_ttl_minutes == -1:
            return False

        delta_minutes = (
            datetime.now() - datetime.fromtimestamp(file.stat().st_mtime)
        ).total_seconds() / 60
        return delta_minutes > self.cache_ttl_minutes

    def _cached_get(self, url: str, *args, **kwargs) -> bytes:
        """
        Proxies a get request. If the item is in the cache and isn't older than the TTL,
        we read the response from there, if not we populate the cache with this response.

        We could do this slickly with middleware and requests,
        but this is simpler, and we don't need anything fancy.
        """
        start = time.perf_counter()
        # basic slugify, this breaks 1:1 mappings between URL:disk cache
        # but for our purposes, this is fine (for example, if 2 URLs differ by a character that's replaced)
        sanitized_path = (
            re.sub(r"[^a-z0-9/]", "_", urlparse(url).path, flags=re.IGNORECASE)
            .lstrip("/")
            .lower()
        )
        # we make an assumption here that we'll only be caching HTML
        # if this is violated, it's annoying for manual inspection but won't break anything
        cached_location = (self.cache_dir / sanitized_path).with_suffix(".cache.html")
        if not cached_location.parent.exists():
            cached_location.parent.mkdir(parents=True, exist_ok=False)

        resp = b""
        if cached_location.exists() and not self._ttl_expired(cached_location):
            resp = cached_location.read_bytes()
            logger.debug(f"cache valid for {url=}")

        # guard against corrupted, empty cached responses
        if len(resp) == 0:
            self.cache_misses += 1
            logger.debug(f"cache not valid or non-existent, populating it for {url=}")
            web_resp = self.http_client.get(url)
            if web_resp.status_code == 200 and len(web_resp.content):
                resp = web_resp.content
                with open(cached_location, "wb") as req_content:
                    req_content.write(resp)
            else:
                raise ValueError(
                    f"request to {url=} failed with non-200 status code {web_resp.status_code=} or empty response"
                )
        else:
            self.cache_hits += 1
        logger.debug(f"took {time.perf_counter() - start:.4f}s to retrieve {url}")
        return resp

    def _get_link_codes_with_prefix(self, url: str, prefix: str) -> list[str]:
        """
        Returns a list of the HREFs of 'a' tags where the href has a given prefix
        """
        soup = BeautifulSoup(self._cached_get(url), "lxml")
        soups = soup.select("a[href]")
        codes = []
        for soup in soups:
            link = soup["href"]
            if link.startswith(prefix):
                code = link[len(prefix) + 1 :].upper()
                if not code:
                    continue
                codes.append(code)
        return codes

    def get_all_faculties(self) -> list[str]:
        """Returns list of faculties, eg ED, BS, ..."""
        return sorted(
            self._get_link_codes_with_prefix(f"{self.ROOT}", "/catalogue/faculty")
        )

    def _get_subjects_from_faculty(self, faculty: str) -> list[str]:
        """Given a faculty, returns all subjects, eg SC -> CMPUT, BIOL, ..."""
        return sorted(
            self._get_link_codes_with_prefix(
                f"{self.ROOT}/faculty/{faculty}", "/catalogue/course"
            )
        )

    def get_all_subjects_from_faculties(self, faculties: list[str]) -> list[str]:
        """Given multiple faculties, return all subjects associated with any of the faculties"""
        subjects = self._process_multithreaded(
            self._get_subjects_from_faculty, faculties
        )
        # some subjects are cross-listed, so we need to eliminate duplicates here
        return sorted(set(subjects))

    def _get_courses_from_subject(self, subject: str) -> list[Course]:
        """Given a subject, returns a list of Course objects eg CMPUT -> CMPUT 174, CMPUT 175"""
        courses_soup = BeautifulSoup(
            self._cached_get(f"{self.ROOT}/course/{subject}"), "lxml"
        )
        # "first" class is important,
        # there are sometimes multiple items for card if the course is changing in the future
        course_titles = courses_soup.select(".course.first h2 > a")
        # eg matches "331" in "AN TR 331", and asserts the subject prefixes the course number
        # eg course_number_pattern = r"CMPUT\s+(\d{1,4}\w{1,3})"
        courses = []
        for course_title in course_titles:
            try:
                course_number_pattern = (
                    re.escape(subject.replace("_", " ")) + r"\s+(\d{1,4}\w{1,3})"
                )
                course_number = re.search(
                    course_number_pattern, course_title.text
                ).group(1)
                courses.append(Course(subject=subject, number=course_number))
            except AttributeError as e:
                raise AttributeError(
                    f"Failed to parse course title {course_title.text=}. "
                    f"Is the selector grabbing the wrong elements? {e=}"
                )
        return courses

    def get_all_courses_from_subjects(self, subjects: list[str]) -> list[Course]:
        """
        Given a list of subjects, returns a list of courses
        Eg [CMPUT, ENGL] -> [CMPUT 174, ENGL 100, ...]
        """
        courses = self._process_multithreaded(self._get_courses_from_subject, subjects)
        return sorted(courses, key=operator.attrgetter("subject", "number"))

    def process_all_course_terms_from_courses(
        self, courses: list[Course]
    ) -> list[dict]:
        """
        Returns a list of all preprocessed information every course in the list
        """
        preprocessed_courses = self._process_multithreaded(
            self._preprocess_course, courses, progress_bar_units="course"
        )
        # sort by course number, term no, section, and finally class id
        # (this makes it easier to diff for changes and spot errors easier)
        return sorted(
            preprocessed_courses,
            key=operator.itemgetter("subject", "catalog", "term", "section", "classId"),
        )

    def _preprocess_course(self, course: Course) -> list[dict]:
        """
        Given a single course object, produces a list of intermediary info
        that can be further processed before inserting into the db
        """
        logger.debug(f"Reading {course}")
        class_objs = []
        course_url = f"{self.ROOT}/course/{course.subject}/{course.number}"
        classes_soup = BeautifulSoup(self._cached_get(course_url), "lxml")
        term_divs = classes_soup.findAll("div", {"class": "mb-5"})
        for term_elem in term_divs:
            term_header = term_elem.find("h2")
            term_name = term_header.text.replace("\n", "").strip()
            term_id = term_header["id"]
            num_conts = len(term_elem.findAll("h3"))
            children = term_elem.findChildren(recursive=False)
            # Workaround to skip "This course is changing in this term...":
            # Seek to the first <h3> and truncate all earlier children
            currChild = 0
            while children[currChild].name != "h3":
                currChild += 1
            children = children[currChild:]
            for i in range(num_conts):
                component_table = children[i * 2 + 1]
                table_body = component_table.find("tbody")
                table_rows = table_body.find_all("tr")
                for tr in table_rows:
                    # Section
                    tr_section = tr.find("td", {"data-card-title": "Section"})
                    tr_section_pattern = (
                        r"^\s*(lecture|lab|lecture/lab|lab/lecture|seminar|clinical|thesis)\s*"  # component type
                        r"([a-z\d]{1,6})\s*"  # section
                        r"\((\d{5})\)"  # class ID
                    )
                    section_search = re.search(
                        tr_section_pattern, tr_section.text, re.IGNORECASE
                    )
                    component, section, class_id = section_search.group(1, 2, 3)

                    # Class times
                    tr_date_time_location_div = tr.find(
                        "td", {"data-card-title": "Dates + Times + Locations"}
                    ).find("div", {"class": "row row-cols-1 row-cols-lg-3"})

                    timing_info_divs = tr_date_time_location_div.find_all(
                        "div", {"class": "col"}
                    )
                    class_times = []
                    num_rows = len(timing_info_divs) // 3
                    for j in range(num_rows):
                        dates, times, loc = (
                            timing_info_divs[j * 3],
                            timing_info_divs[j * 3 + 1],
                            timing_info_divs[j * 3 + 2],
                        )
                        class_times.append(
                            (dates.text.strip(), times.text.strip(), loc.text.strip())
                        )

                    instructor = None
                    tr_instructors = tr.find("td", {"data-card-title": "Instructor(s)"})
                    if instructors_div := tr_instructors.find("a"):
                        instructor = instructors_div.text.strip()

                    class_objs.append(
                        {
                            "catalog": course.number,
                            "classId": class_id,
                            "component": component,
                            "section": section,
                            "instructor": instructor,
                            "classTimes": class_times,
                            "subject": course.subject,
                            "term": term_id,
                            "termName": term_name,
                        }
                    )
        return class_objs

    def _process_multithreaded(
        self,
        fn: Callable[[Any], list[Any]],
        input_data: list,
        progress_bar_units: str | None = None,
    ) -> list:
        """
        Given a list of input data and a function to process that data with,
         processing the data with a ThreadPoolExecutor.

        If progress_bar_units is specified, a progress bar is shown with those units

        Returns a list of results
        """
        if progress_bar_units is not None:
            partial_tqdm = partial(
                tqdm,
                unit_scale=True,
                unit=progress_bar_units,
                total=len(input_data),
                smoothing=0.25,
            )
        else:
            partial_tqdm = lambda x: x
        result = []
        with futures.ProcessPoolExecutor(max_workers=self.max_workers) as exe:
            # map the future to the subject, that way we can tell what subject failed
            fut_to_input = {exe.submit(fn, x): x for x in input_data}

            for fut in partial_tqdm(concurrent.futures.as_completed(fut_to_input)):
                try:
                    result.extend(fut.result())
                except Exception as e:
                    input_obj = fut_to_input[fut]
                    logger.error(f"scraping {input_obj=} failed: {e}")
        return result


def cli():
    # formatter_class shows defaults when script is run with --help
    parser = argparse.ArgumentParser(
        description="scrape", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--debug", action="store_true", help="Enable debugging mode.")
    parser.add_argument(
        "--cache-ttl",
        type=float,
        default=24 * 60,
        help="Life (in minutes) of cache entry before it's invalidated. "
        "A TTL of 0 will always invalidate the cache, and a TTL of -1 will never invalidate the cache.",
    )
    parser.add_argument(
        "--max-workers",
        "-j",
        type=int,
        default=3,
        help="Number of maximum workers to use for scraping course pages",
    )
    parser.add_argument(
        "--scrape-root",
        type=str,
        default=Path(__file__).parent.parent / "local",
        help="Base directory to store scraper cache and output",
    )
    parser.add_argument(
        "--use-processes",
        action="store_true",
        help="uses processes instead of threads for the parallel compute implementation. "
        "This is only recommended when you know most things you are going to access will be cached, "
        "as this disables sharing HTTP sessions. Higher -j recommended in conjunction with this flag",
    )
    args = parser.parse_args()
    main(args)


def main(args):
    """
    Main scraping routine.

    URLs are cached on-demand via Scraper._cached_get

    You can think of the course data as a tree:
        (faculty -> subject -> course num -> course info), we discover it in a BFS manner
    Each level uses multithreading to speed up the process.
    """
    debug = args.debug
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.debug("debug mode is active")
    logger.debug(f"{args=}")
    cache_ttl_text = (
        str(timedelta(seconds=args.cache_ttl * 60))
        if args.cache_ttl > 0
        else "infinite"
    )
    logger.info(f"max_workers={args.max_workers} cache_ttl=(cache_ttl_text)")
    root = Path(args.scrape_root).absolute()
    scraper = Scraper(
        cache_dir=root / ".cache",
        cache_ttl_minutes=args.cache_ttl,
        max_workers=args.max_workers,
        use_processes=args.use_processes,
    )
    start = time.perf_counter()

    f_time = time.perf_counter()
    logger.info("retrieving faculties")
    faculties = scraper.get_all_faculties()
    logger.info(f"retrieving faculties took {time.perf_counter() - f_time:.2f}s")

    s_time = time.perf_counter()
    logger.info(f"retrieving subjects from {len(faculties)} faculties")
    subjects = scraper.get_all_subjects_from_faculties(faculties)
    logger.info(f"retrieving subjects took {time.perf_counter() - s_time:.2f}s")

    c_time = time.perf_counter()
    logger.info(f"retrieving courses from {len(subjects)} subjects")
    courses = scraper.get_all_courses_from_subjects(subjects)
    logger.info(f"retrieving courses took {time.perf_counter() - c_time:.2f}s")

    p_time = time.perf_counter()
    logger.info(f"processing {len(courses)} courses")
    course_instances = scraper.process_all_course_terms_from_courses(courses)
    logger.info(
        f"processing {len(course_instances)} course terms took {time.perf_counter() - p_time:.2f}s"
    )

    if len(course_instances) > 0:
        with open(root / "raw.json", "w") as raw:
            json.dump(course_instances, raw, sort_keys=True, indent=4)
    else:
        logger.warning("no preprocessed course instances produced, skipping write")
    logger.info(f"completed in {time.perf_counter() - start:.2f}s")


if __name__ == "__main__":
    cli()
