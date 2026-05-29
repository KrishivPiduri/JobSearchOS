import time
import random
import re
import requests
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Initialize global UserAgent
ua = UserAgent()


# Cache implementation
class JobCache:
    def __init__(self):
        self.cache = {}
        self.TTL = 60 * 60  # 1 hour in seconds

    def set(self, key, value):
        self.cache[key] = {
            "data": value,
            "timestamp": time.time()
        }

    def get(self, key):
        item = self.cache.get(key)
        if not item:
            return None

        # Check if cache expired
        if time.time() - item["timestamp"] > self.TTL:
            del self.cache[key]
            return None

        return item["data"]

    def clear(self):
        now = time.time()
        keys_to_delete = [
            key for key, value in self.cache.items()
            if now - value["timestamp"] > self.TTL
        ]
        for key in keys_to_delete:
            del self.cache[key]


# Initialize global cache
cache = JobCache()


# Main Query Class
class Query:
    def __init__(self, query_obj):
        self.host = query_obj.get("host", "www.linkedin.com")

        keyword = query_obj.get("keyword", "")
        self.keyword = re.sub(r'\s+', '+', keyword.strip()) if keyword else ""

        location = query_obj.get("location", "")
        self.location = re.sub(r'\s+', '+', location.strip()) if location else ""

        self.date_since_posted = query_obj.get("dateSincePosted", "")
        self.job_type = query_obj.get("jobType", "")
        self.remote_filter = query_obj.get("remoteFilter", "")
        self.salary = query_obj.get("salary", "")
        self.experience_level = query_obj.get("experienceLevel", "")
        self.sort_by = query_obj.get("sortBy", "")
        self.limit = int(query_obj.get("limit", 0))
        self.page = int(query_obj.get("page", 0))
        self.has_verification = query_obj.get("has_verification", False)
        self.under_10_applicants = query_obj.get("under_10_applicants", False)

    def get_cache_key(self):
        return f"{self.url(0)}_limit:{self.limit}"

    def get_date_since_posted(self):
        date_range = {
            "past month": "r2592000",
            "past week": "r604800",
            "24hr": "r86400",
        }
        return date_range.get(str(self.date_since_posted).lower(), "")

    def get_experience_level(self):
        experience_range = {
            "internship": "1",
            "entry level": "2",
            "associate": "3",
            "senior": "4",
            "director": "5",
            "executive": "6",
        }
        return experience_range.get(str(self.experience_level).lower(), "")

    def get_job_type(self):
        job_type_range = {
            "full time": "F",
            "full-time": "F",
            "part time": "P",
            "part-time": "P",
            "contract": "C",
            "temporary": "T",
            "volunteer": "V",
            "internship": "I",
        }
        return job_type_range.get(str(self.job_type).lower(), "")

    def get_remote_filter(self):
        remote_filter_range = {
            "on-site": "1",
            "on site": "1",
            "remote": "2",
            "hybrid": "3",
        }
        return remote_filter_range.get(str(self.remote_filter).lower(), "")

    def get_salary(self):
        salary_range = {
            "40000": "1",
            "60000": "2",
            "80000": "3",
            "100000": "4",
            "120000": "5",
        }
        return salary_range.get(str(self.salary), "")

    def get_has_verification(self):
        return "true" if self.has_verification else "false"

    def get_under_10_applicants(self):
        return "true" if self.under_10_applicants else "false"

    def get_page(self):
        return self.page * 25

    def url(self, start):
        base_url = f"https://{self.host}/jobs-guest/jobs/api/seeMoreJobPostings/search"
        params = {}

        if self.keyword: params["keywords"] = self.keyword
        if self.location: params["location"] = self.location

        date_val = self.get_date_since_posted()
        if date_val: params["f_TPR"] = date_val

        salary_val = self.get_salary()
        if salary_val: params["f_SB2"] = salary_val

        exp_val = self.get_experience_level()
        if exp_val: params["f_E"] = exp_val

        remote_val = self.get_remote_filter()
        if remote_val: params["f_WT"] = remote_val

        job_type_val = self.get_job_type()
        if job_type_val: params["f_JT"] = job_type_val

        if self.has_verification: params["f_VJ"] = self.get_has_verification()
        if self.under_10_applicants: params["f_EA"] = self.get_under_10_applicants()

        params["start"] = start + self.get_page()

        if self.sort_by == "recent":
            params["sortBy"] = "DD"
        elif self.sort_by == "relevant":
            params["sortBy"] = "R"

        query_string = urlencode(params)
        return f"{base_url}?{query_string}"

    def get_jobs(self):
        all_jobs = []
        start = 0
        batch_size = 25
        has_more = True
        consecutive_errors = 0
        max_consecutive_errors = 3

        print(self.url(0))
        print(self.get_cache_key())

        try:
            # Check cache first
            cache_key = self.get_cache_key()
            cached_jobs = cache.get(cache_key)
            if cached_jobs:
                print("Returning cached results")
                return cached_jobs

            while has_more:
                try:
                    jobs = self.fetch_job_batch(start)

                    if not jobs or len(jobs) == 0:
                        has_more = False
                        break

                    all_jobs.extend(jobs)
                    print(f"Fetched {len(jobs)} jobs. Total: {len(all_jobs)}")

                    if self.limit and len(all_jobs) >= self.limit:
                        all_jobs = all_jobs[:self.limit]
                        break

                    # Reset error counter on successful fetch
                    consecutive_errors = 0
                    start += batch_size

                    # Add reasonable delay between requests
                    time.sleep((2000 + random.random() * 1000) / 1000.0)

                except Exception as e:
                    consecutive_errors += 1
                    print(f"Error fetching batch (attempt {consecutive_errors}): {str(e)}")

                    if consecutive_errors >= max_consecutive_errors:
                        print("Max consecutive errors reached. Stopping.")
                        break

                    # Exponential backoff
                    time.sleep(2 ** consecutive_errors)

            # Cache results if we got any
            if len(all_jobs) > 0:
                cache.set(self.get_cache_key(), all_jobs)

            return all_jobs

        except Exception as e:
            print(f"Fatal error in job fetching: {str(e)}")
            raise e

    def fetch_job_batch(self, start):
        headers = {
            "User-Agent": ua.random,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.linkedin.com/jobs",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

        try:
            response = requests.get(self.url(start), headers=headers, timeout=10)

            if response.status_code == 429:
                raise Exception("Rate limit reached")
            response.raise_for_status()

            return parse_job_list(response.text)
        except Exception as e:
            raise e


# Parsing utility
def parse_job_list(job_data):
    try:
        soup = BeautifulSoup(job_data, "html.parser")
        jobs_elements = soup.find_all("li")
        parsed_jobs = []

        for index, job in enumerate(jobs_elements):
            try:
                title_el = job.find(class_="base-search-card__title")
                position = title_el.get_text(strip=True) if title_el else None

                company_el = job.find(class_="base-search-card__subtitle")
                company = company_el.get_text(strip=True) if company_el else None

                location_el = job.find(class_="job-search-card__location")
                location = location_el.get_text(strip=True) if location_el else None

                date_el = job.find("time")
                date = date_el["datetime"] if date_el and date_el.has_attr("datetime") else None

                salary_el = job.find(class_="job-search-card__salary-info")
                salary = re.sub(r'\s+', ' ', salary_el.get_text(strip=True)) if salary_el else "Not specified"

                link_el = job.find(class_="base-card__full-link")
                job_url = link_el["href"] if link_el and link_el.has_attr("href") else ""

                img_el = job.find(class_="artdeco-entity-image")
                company_logo = img_el["data-delayed-url"] if img_el and img_el.has_attr("data-delayed-url") else ""

                ago_time_el = job.find(class_="job-search-card__listdate")
                ago_time = ago_time_el.get_text(strip=True) if ago_time_el else ""

                # Only return job if we have at least position and company
                if not position or not company:
                    continue

                parsed_jobs.append({
                    "position": position,
                    "company": company,
                    "location": location,
                    "date": date,
                    "salary": salary,
                    "jobUrl": job_url,
                    "companyLogo": company_logo,
                    "agoTime": ago_time,
                })
            except Exception as err:
                print(f"Error parsing job at index {index}: {str(err)}")
                continue

        return parsed_jobs
    except Exception as error:
        print(f"Error parsing job list: {str(error)}")
        return []




# Public/Exported Functions
def query(query_object):
    q = Query(query_object)
    return q.get_jobs()


def clear_cache():
    cache.clear()


def get_cache_size():
    return len(cache.cache)


import os

# File to store the URLs of jobs we've already seen
SEEN_JOBS_FILE = "seen_jobs.txt"


def load_seen_jobs():
    """Loads previously seen base URLs from the text file into a set."""
    if not os.path.exists(SEEN_JOBS_FILE):
        return set()
    with open(SEEN_JOBS_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())


def save_seen_job(url):
    """Appends a new base URL to the text file."""
    with open(SEEN_JOBS_FILE, "a") as f:
        f.write(f"{url}\n")


def get_base_url(url):
    """Removes tracking parameters from LinkedIn URLs for accurate deduplication."""
    if not url:
        return ""
    return url.split('?')[0]


def track_new_jobs(search_params_list):
    """
    Takes a list of search parameter dictionaries, queries LinkedIn,
    and prints only the URLs of jobs that haven't been output before.
    """
    seen_urls = load_seen_jobs()
    total_new_jobs = 0

    for params in search_params_list:
        keyword = params.get("keyword", "Any")
        location = params.get("location", "Any")

        print(f"\n--- Searching: '{keyword}' in '{location}' ---")

        # Call the query function from the previous script
        try:
            results = query(params)
        except Exception as e:
            print(f"Error fetching jobs for {keyword}: {e}")
            continue

        new_in_batch = 0
        for job in results:
            raw_url = job.get("jobUrl")
            if not raw_url:
                continue

            # Clean the URL to ensure accurate deduplication
            base_url = get_base_url(raw_url)

            if base_url not in seen_urls:
                print(base_url)

                # Update our tracking state immediately
                seen_urls.add(base_url)
                save_seen_job(base_url)

                new_in_batch += 1
                total_new_jobs += 1

        print(f"Found {new_in_batch} new jobs for this query.")

    print(f"\nFinished processing. Printed {total_new_jobs} total new job URLs.")


# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    # Define your list of search configurations
    my_searches = [
        {
            "keyword": "python developer",
            "location": "San Jose, CA",
            "dateSincePosted": "past week",
            "limit": 10
        },
        {
            "keyword": "backend engineer python",
            "location": "San Francisco, CA",
            "limit": 5
        },
        {
            "keyword": "django developer",
            "location": "remote",
            "dateSincePosted": "24hr",
            "limit": 25
        }
    ]

    # Run the tracker
    track_new_jobs(my_searches)