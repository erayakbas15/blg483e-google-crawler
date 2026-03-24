# Google in a Day: Native Python Crawler & Search Engine

[cite_start]This project is a functional web crawler and real-time search engine built for the **ITU AI-Aided Computer Engineering** course. [cite: 1, 4] [cite_start]It uses strictly native Python libraries to manage concurrent crawling, back-pressure, and thread-safe indexing. [cite: 41, 49]

## How to Run
1. Ensure you have Python 3.10+ installed.
2. Open your terminal in the project directory.
3. Run the server: `python search_system.py`
4. Visit `http://localhost:3600` in your browser.

## Features
- [cite_start]**Concurrent Crawler:** Handles multiple threads to index pages to a specific depth k. [cite: 35, 48]
- **Sharded Storage:** Saves word data alphabetically in `data/storage/` for fast retrieval.
- [cite_start]**Real-time Search:** Search for words while the crawler is active, with results ranked by a custom relevancy formula. [cite: 47, 51]
- [cite_start]**Monitoring:** Live dashboard to track progress, queue depth, and back-pressure status. [cite: 65, 66, 69]

**GitHub Repository:** https://github.com/erayakbas15/blg483e-google-crawler