# Google in a Day: Native Python Crawler & Search Engine

This project is a functional web crawler and real-time search engine built for the ITU AI-Aided Computer Engineering course. It uses strictly native Python libraries to manage concurrent crawling, back-pressure, and thread-safe indexing.

## How to Run

1. Ensure you have Python 3.10+ installed.
2. Open your terminal in the project directory.
3. Run the server: `python search_system.py`
4. Visit `http://localhost:3600` in your browser.

## Features

* **Concurrent Crawler:** Handles multiple threads to index pages to a specific depth k.
* **Sharded Storage:** Saves word data alphabetically in `data/storage/` for fast retrieval.
* **Real-time Search:** Search for words while the crawler is active, with results ranked by a custom relevancy formula.
* **Monitoring:** Live dashboard to track progress, queue depth, and back-pressure status.

**GitHub Repository:** https://github.com/erayakbas15/blg483e-google-crawler