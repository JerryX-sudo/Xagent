"""Web tools for Xagent."""

import urllib.request
import urllib.parse
import json
import re
import ssl
import os
from typing import Any
from html.parser import HTMLParser

from tools.base import BaseTool

# Create a default SSL context that doesn't verify (for environments with proxy issues)
try:
    _ssl_context = ssl.create_default_context()
    _ssl_context.check_hostname = False
    _ssl_context.verify_mode = ssl.CERT_NONE
except Exception:
    _ssl_context = None


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

            with urllib.request.urlopen(req, timeout=10, context=_ssl_context) as response:
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
    """Tool for web search (using DuckDuckGo API)."""

    name = "web_search"
    description = "Search the web. Returns search results with titles, URLs and snippets."
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

        # Try DuckDuckGo Instant Answer API first (faster, no HTML parsing)
        result = self._search_ddg_api(query, max_results)
        if result:
            return result

        # Fallback to HTML search
        result = self._search_ddg_html(query, max_results)
        if result:
            return result

        return f"Could not search for: {query}. Network may be unavailable."

    def _search_ddg_api(self, query: str, max_results: int) -> str | None:
        """Search using DuckDuckGo Instant Answer API."""
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"

            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                }
            )

            with urllib.request.urlopen(req, timeout=15, context=_ssl_context) as response:
                data = json.loads(response.read().decode('utf-8'))

            results = []

            # Abstract (main answer)
            if data.get('Abstract'):
                results.append(f"**{data.get('Heading', 'Answer')}**\n{data['Abstract']}\nSource: {data.get('AbstractURL', '')}")

            # Related topics
            for topic in data.get('RelatedTopics', [])[:max_results]:
                if isinstance(topic, dict) and topic.get('Text'):
                    text = topic['Text']
                    url = topic.get('FirstURL', '')
                    results.append(f"- {text}\n  {url}")

            if results:
                return f"Search results for '{query}':\n\n" + "\n\n".join(results)

            return None

        except Exception:
            return None

    def _search_ddg_html(self, query: str, max_results: int) -> str | None:
        """Search using DuckDuckGo HTML (fallback)."""
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                }
            )

            with urllib.request.urlopen(req, timeout=20, context=_ssl_context) as response:
                content = response.read().decode('utf-8', errors='ignore')

            results = []
            pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
            matches = re.findall(pattern, content)

            for result_url, title in matches[:max_results]:
                if 'uddg=' in result_url:
                    result_url = urllib.parse.unquote(result_url.split('uddg=')[-1].split('&')[0])
                title = title.strip()
                if title and result_url:
                    results.append(f"- {title}\n  {result_url}")

            if results:
                return f"Search results for '{query}':\n\n" + "\n\n".join(results)

            return None

        except Exception:
            return None
