import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from crawler import CrawlerManager, ensure_dirs
from search import sanitize_query_word, search_word


PORT = 3600
manager = CrawlerManager()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "index.html")


class ApiHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, payload):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_html_file(self, path):
        if not os.path.exists(path):
            self._send_json(404, {"error": "index.html not found"})
            return
        with open(path, "rb") as f:
            raw = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/":
            self._send_html_file(INDEX_FILE)
            return

        if parsed.path == "/search":
            params = urllib.parse.parse_qs(parsed.query)
            query = params.get("query", [""])[0]
            sort_by = params.get("sortBy", ["relevance"])[0]
            if sort_by != "relevance":
                self._send_json(400, {"error": "Only sortBy=relevance is supported"})
                return
            results = search_word(query)
            self._send_json(200, {"query": sanitize_query_word(query), "results": results})
            return

        if parsed.path == "/crawl":
            params = urllib.parse.parse_qs(parsed.query)
            origin = params.get("origin", [""])[0]
            max_depth = params.get("maxDepth", ["1"])[0]
            hit_rate = params.get("hitRate", ["0.25"])[0]
            max_queue = params.get("maxQueue", ["100"])[0]
            if not origin:
                self._send_json(400, {"error": "origin is required"})
                return
            try:
                crawler_id = manager.create_job(
                    origin_url=origin,
                    max_depth=int(max_depth),
                    hit_rate=float(hit_rate),
                    max_queue=int(max_queue),
                )
            except ValueError:
                self._send_json(400, {"error": "maxDepth, hitRate and maxQueue must be numeric"})
                return
            self._send_json(200, {"crawlerId": crawler_id, "origin": origin})
            return

        if parsed.path == "/status":
            statuses = manager.list_statuses()
            self._send_json(200, {"jobs": statuses})
            return

        self._send_json(404, {"error": "Not found"})

    def log_message(self, format_str, *args):
        return


def run_server():
    ensure_dirs()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), ApiHandler)
    print(f"Search API listening on http://127.0.0.1:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
