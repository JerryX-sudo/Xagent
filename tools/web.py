"""Web tools for Xagent."""

import urllib.request
import urllib.parse
import json
import re
from typing import Any
from html.parser import HTMLParser

from tools.base import BaseTool


class HTMLTextExtractor(HTMLParser):
    """Extract text from HTML."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip_tags = {'script', 'style', 'head', 'meta', 'link'}
        self._current_tag = None

    def handle_starttag(self, tag, attrs):
        self._current_tag = tag

    def handle_endtag(self, tag):
        self._current_tag = None

    def handle_data(self, data):
        if self._current_tag not in self._skip_tags:
            text = data.strip()
            if text:
                self.text_parts.append(text)

    def get_text(self) -> str:
        return ' '.join(self.text_parts)


class WebFetchTool(BaseTool):
    """Tool for fetching web page content."""

    name = "web_fetch"
    description = "Fetch content from a URL. Returns the text content of the page."
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch",
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum content length to return (default: 5000)",
            },
        },
        "required": ["url"],
    }

    def run(self, **kwargs: Any) -> str:
        """Fetch URL content."""
        url = kwargs.get("url", "")
        max_length = kwargs.get("max_length", 5000)

        if not url:
            return "Error: url required"

        # Validate URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; Xagent/1.0)',
                    'Accept': 'text/html,application/xhtml+xml,text/plain',
                }
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                content_type = response.headers.get('Content-Type', '')
                encoding = 'utf-8'

                # Try to get encoding from content-type
                if 'charset=' in content_type:
                    encoding = content_type.split('charset=')[-1].split(';')[0]

                content = response.read().decode(encoding, errors='ignore')

                # Extract text from HTML
                if 'html' in content_type:
                    extractor = HTMLTextExtractor()
                    extractor.feed(content)
                    text = extractor.get_text()
                else:
                    text = content

                # Truncate if needed
                if len(text) > max_length:
                    text = text[:max_length] + f"\n... (truncated, {len(text) - max_length} chars omitted)"

                return text

        except urllib.error.HTTPError as e:
            return f"Error: HTTP {e.code} - {e.reason}"
        except urllib.error.URLError as e:
            return f"Error: {e.reason}"
        except Exception as e:
            return f"Error: {e}"


class WebSearchTool(BaseTool):
    """Tool for web search (using DuckDuckGo)."""

    name = "web_search"
    description = "Search the web using DuckDuckGo. Returns search results with titles and URLs."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 5)",
            },
        },
        "required": ["query"],
    }

    def run(self, **kwargs: Any) -> str:
        """Perform web search."""
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 5)

        if not query:
            return "Error: query required"

        try:
            # Use DuckDuckGo HTML search
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; Xagent/1.0)',
                }
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8', errors='ignore')

            # Parse results (simple regex extraction)
            results = []

            # Find result links
            pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
            matches = re.findall(pattern, content)

            for url, title in matches[:max_results]:
                # Clean up URL (DuckDuckGo wraps URLs)
                if 'uddg=' in url:
                    url = urllib.parse.unquote(url.split('uddg=')[-1].split('&')[0])
                title = title.strip()
                if title and url:
                    results.append(f"- {title}\n  {url}")

            if not results:
                return f"No results found for: {query}"

            return f"Search results for '{query}':\n\n" + "\n\n".join(results)

        except Exception as e:
            return f"Error searching: {e}"
