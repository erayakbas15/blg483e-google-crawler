Product Requirements Document (PRD): Google in a Day (Python)
1. Overview
This project is a concurrent web crawler and real-time search engine built strictly using Python's native capabilities. It is designed to demonstrate architectural sensibility, thread-safe data management, and the handling of back-pressure without relying on high-level external scraping libraries (like Scrapy or BeautifulSoup).

The system consists of two main services running concurrently: a Crawler Service that indexes web pages into a file-based storage system, and a Search Service that queries this local storage to return ranked results.

2. System Architecture
The application will be built using Python 3.10+. To provide the required UI and API capabilities, we will use a lightweight web framework (e.g., native http.server or FastAPI for robust backend routing).

Concurrency: Python's native threading module will manage multiple crawler jobs.

Data Structures: queue.Queue will be used for URL frontier management to inherently handle thread-safe FIFO operations. threading.Lock will be used to prevent race conditions during file writing.

Storage (File-Based NoSQL Approach): Instead of a relational DB, the system will use a local file system under a data/storage/ directory to manage state and indexing.

3. Core Components
3.1. Crawler Service (Indexer)
Job Creation: Initiates a new crawler thread given an origin_url and max_depth.

Identification: Each job generates a unique ID format: {EpochTime}_{ThreadID}.

State Management:

visited_urls.data: A globally shared, thread-safe file tracking all visited URLs to prevent redundant crawling.

[crawlerId]_status.json: Tracks the live status (queued, visited, active, finished).

[crawlerId].log: Tracks runtime events and errors.

Crawling Logic: * Uses native urllib.request to fetch HTML.

Uses native html.parser to extract text and hyperlink tags.

Indexing Logic (Alphabetical Sharding): Words extracted from pages are stored in files categorized by their first letter (e.g., A.data, B.data).

Format per entry: {"word": "apple", "url": "...", "origin": "...", "depth": 1, "frequency": 12}.

Back-Pressure: Implements a maximum queue size and a sleep/delay mechanism (hit rate) between requests to prevent system overload.

3.2. Search Service (Searcher)
Concurrent Execution: Must be able to read from the .data files while the Crawler Service is actively writing to them (requires careful file-locking or append-only reading).

Query Processing: Accepts a string query, sanitizes it, and determines the initial letter to locate the correct storage file (e.g., query "machine" -> reads M.data).

Ranking (Heuristic): Parses the relevant .data file and returns a list of triples (relevant_url, origin_url, depth) sorted descendingly by the frequency count of the matched word.

3.3. User Interface (UI)
A simple web-based dashboard (HTML/JS) served by the Python backend.

Crawler View: Input fields to start a new job (URL, depth, hit rate limit). Displays a list of historical/running crawler jobs.

Status View: Long-polling or auto-refreshing page fetching data from [crawlerId]_status.json to show active queue depth, URLs processed, and logs.

Search View: A search bar returning ranked results based on the file-system index.

4. Technical Constraints
No High-Level Scraping Libs: Strictly native urllib and html.parser.

Data Corruption Prevention: Explicit use of Mutexes (Lock) when appending to the alphabetical data files or updating visited_urls.data.

Resumability: Because state is continuously flushed to the data/ directory, a restarted server will not lose previously indexed words or the visited URL registry.