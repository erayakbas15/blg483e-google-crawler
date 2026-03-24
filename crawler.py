import json
import os
import queue
import threading
import urllib.parse
import urllib.request
from html.parser import HTMLParser


DATA_DIR = os.path.join("data")
STORAGE_DIR = os.path.join(DATA_DIR, "storage")
JOBS_DIR = os.path.join(DATA_DIR, "jobs")
VISITED_FILE = os.path.join(DATA_DIR, "visited_urls.data")


def ensure_dirs():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    os.makedirs(JOBS_DIR, exist_ok=True)
    if not os.path.exists(VISITED_FILE):
        with open(VISITED_FILE, "a", encoding="utf-8"):
            pass


def tokenize_text(text):
    tokens = []
    current = []
    for ch in text.lower():
        if ("a" <= ch <= "z") or ("0" <= ch <= "9"):
            current.append(ch)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))
    return tokens


class HtmlContentParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.words = []
        self.links = []

    def handle_data(self, data):
        self.words.extend(tokenize_text(data))

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value.strip())


class CrawlerJob:
    def __init__(self, manager, crawler_id, origin_url, max_depth, hit_rate, max_queue):
        self.manager = manager
        self.crawler_id = crawler_id
        self.origin_url = origin_url
        self.max_depth = int(max_depth)
        self.hit_rate = float(hit_rate)
        self.frontier = queue.Queue(maxsize=int(max_queue))
        self.status_file = os.path.join(JOBS_DIR, f"{crawler_id}_status.json")
        self.log_file = os.path.join(JOBS_DIR, f"{crawler_id}.log")
        self.local_seen = set()
        self.active_workers = 0
        self.active_lock = threading.Lock()
        self.stop_event = threading.Event()

    def start(self, workers=3):
        self._enqueue(self.origin_url, 0)
        self._save_status("queued", 0, 0, 0)

        thread = threading.Thread(target=self._run, args=(workers,), daemon=True)
        thread.start()
        return thread

    def _run(self, workers):
        for _ in range(workers):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()

        self.frontier.join()
        self.stop_event.set()
        self._save_status("finished", self.frontier.qsize(), len(self.local_seen), 0)
        self._log("job finished")

    def _worker(self):
        while not self.stop_event.is_set():
            try:
                url, depth = self.frontier.get(timeout=0.5)
            except queue.Empty:
                continue

            with self.active_lock:
                self.active_workers += 1
                active = self.active_workers
            self._save_status("active", self.frontier.qsize(), len(self.local_seen), active)

            try:
                self._crawl_url(url, depth)
            except Exception as exc:
                self._log(f"error crawling {url}: {exc}")
            finally:
                with self.active_lock:
                    self.active_workers -= 1
                    active = self.active_workers
                self.frontier.task_done()
                if self.frontier.qsize() > 0:
                    state = "queued"
                elif active > 0:
                    state = "active"
                else:
                    state = "visited"
                self._save_status(state, self.frontier.qsize(), len(self.local_seen), active)

    def _crawl_url(self, url, depth):
        if depth > self.max_depth:
            return

        if not self.manager.mark_visited(url):
            return

        self.local_seen.add(url)
        self._log(f"visiting depth={depth} url={url}")

        req = urllib.request.Request(url, headers={"User-Agent": "NativeCrawler/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return
            html = response.read().decode("utf-8", errors="ignore")

        parser = HtmlContentParser()
        parser.feed(html)

        frequencies = {}
        for word in parser.words:
            frequencies[word] = frequencies.get(word, 0) + 1
        self.manager.write_index(url, self.origin_url, depth, frequencies)

        if depth >= self.max_depth:
            return

        for href in parser.links:
            abs_url = urllib.parse.urljoin(url, href)
            if abs_url.startswith("http://") or abs_url.startswith("https://"):
                self._enqueue(abs_url, depth + 1)

    def _enqueue(self, url, depth):
        if url in self.local_seen:
            return
        try:
            self.frontier.put((url, depth), timeout=0.2)
        except queue.Full:
            self._log(f"frontier full, skipping {url}")
            return

        if self.hit_rate > 0:
            threading.Event().wait(self.hit_rate)

    def _save_status(self, state, queued, visited, active):
        payload = {
            "crawlerId": self.crawler_id,
            "state": state,
            "origin": self.origin_url,
            "maxDepth": self.max_depth,
            "queued": queued,
            "visited": visited,
            "active": active,
        }
        with self.manager.status_lock:
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump(payload, f)

    def _log(self, message):
        with self.manager.log_lock:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{message}\n")


class CrawlerManager:
    def __init__(self):
        self.visited_lock = threading.Lock()
        self.storage_lock = threading.Lock()
        self.status_lock = threading.Lock()
        self.log_lock = threading.Lock()
        self.jobs = {}
        self.job_counter = 0

    def _next_job_id(self):
        with self.status_lock:
            self.job_counter += 1
            return f"{self.job_counter}_{threading.get_ident()}"

    def mark_visited(self, url):
        with self.visited_lock:
            with open(VISITED_FILE, "r", encoding="utf-8") as f:
                visited_urls = {line.strip() for line in f if line.strip()}
            if url in visited_urls:
                return False
            with open(VISITED_FILE, "a", encoding="utf-8") as f:
                f.write(url + "\n")
            return True

    def write_index(self, url, origin, depth, frequencies):
        with self.storage_lock:
            for word, freq in frequencies.items():
                shard = word[0].lower() if word else "_"
                if not ("a" <= shard <= "z"):
                    shard = "_"
                path = os.path.join(STORAGE_DIR, f"{shard}.data")
                with open(path, "a", encoding="utf-8") as f:
                    # Required exact line format: word url origin depth frequency
                    f.write(f"{word} {url} {origin} {depth} {freq}\n")

    def create_job(self, origin_url, max_depth=1, hit_rate=0.25, max_queue=100):
        crawler_id = self._next_job_id()
        job = CrawlerJob(self, crawler_id, origin_url, max_depth, hit_rate, max_queue)
        self.jobs[crawler_id] = job
        job.start()
        return crawler_id

    def list_statuses(self):
        statuses = []
        if not os.path.isdir(JOBS_DIR):
            return statuses
        for filename in os.listdir(JOBS_DIR):
            if not filename.endswith("_status.json"):
                continue
            full_path = os.path.join(JOBS_DIR, filename)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                statuses.append(payload)
            except (OSError, json.JSONDecodeError):
                continue
        statuses.sort(key=lambda item: item.get("crawlerId", ""), reverse=True)
        return statuses
