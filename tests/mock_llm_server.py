# Copyright (c) 2026
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Minimal OpenAI-compatible mock server for functional CLI tests.

The CI workflow starts this server before running
`tests/test_functional_llm_mock.py`. It intentionally implements only the
endpoints required by the test:

- `GET /ping` for readiness probing
- `POST */chat/completions` for LiteLLM OpenAI-style completion calls
"""

from __future__ import annotations

import argparse
import json
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockLLMRequestHandler(BaseHTTPRequestHandler):
    """Serve a narrow subset of OpenAI-compatible API endpoints."""

    server_version = "MockLLM/1.0"

    def do_GET(self) -> None:
        """Handle readiness probes."""
        if self.path == "/ping":
            self._write_json(HTTPStatus.OK, {"status": "ok"})
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        """Return a deterministic completion response for chat requests."""
        if not self.path.endswith("/chat/completions"):
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        body = self._read_json_body()
        if body is None:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "invalid json"})
            return

        model = str(body.get("model", "openai/gpt-4o-mini"))
        response = {
            "id": "chatcmpl-mock-1",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Updated release notes with concise commit summary.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 42,
                "completion_tokens": 10,
                "total_tokens": 52,
            },
        }
        self._write_json(HTTPStatus.OK, response)

    def _read_json_body(self) -> dict[str, object] | None:
        """Read and decode the request body as JSON."""
        content_length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            parsed = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

        if not isinstance(parsed, dict):
            return None
        return parsed

    def _write_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        """Send a JSON response with the provided status code."""
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        """Disable default noisy request logging in CI output."""
        return


def parse_args() -> argparse.Namespace:
    """Parse command-line options for host and port."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    return parser.parse_args()


def main() -> None:
    """Run the mock HTTP server until interrupted."""
    args = parse_args()
    with ThreadingHTTPServer((args.host, args.port), MockLLMRequestHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
