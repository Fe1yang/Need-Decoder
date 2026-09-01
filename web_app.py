"""Small local web interface for demonstrating Need Decoder."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from need_decoder.text import search_terms
from starter.agent import Agent


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
DEFAULT_CATALOG = ROOT / "data" / "catalog.jsonl"
DEFAULT_PROFILE = {
    "purchase_frequency": "3-4 prior purchases",
    "average_prior_rating": 4.5,
    "rating_style": "usually positive",
    "preference_tags": ["comfort", "durability", "style"],
    "summary": "Prior purchases emphasize comfort, durability, and style.",
}


class NeedDecoderApplication:
    def __init__(self, catalog_path: Path) -> None:
        self.catalog_path = catalog_path
        self.agent = Agent(catalog_path)
        self.products = self._load_products(catalog_path)
        self.lock = threading.Lock()

    @staticmethod
    def _load_products(catalog_path: Path) -> dict[str, dict]:
        products: dict[str, dict] = {}
        with catalog_path.open(encoding="utf-8") as catalog:
            for line in catalog:
                try:
                    product = json.loads(line)
                except json.JSONDecodeError:
                    continue
                products[str(product["parent_asin"])] = product
        return products

    def reset(self, session_id: str) -> dict:
        with self.lock:
            self.agent.reset(session_id, DEFAULT_PROFILE)
            state = self.agent.inspect_session(session_id)
        return {"session_id": session_id, "state": state}

    def chat(self, session_id: str, message: str, turn: int, top_k: int = 3) -> dict:
        with self.lock:
            if session_id not in self.agent.sessions:
                self.agent.reset(session_id, DEFAULT_PROFILE)
            response = self.agent.respond(session_id, message, turn, top_k=top_k)
            state = self.agent.inspect_session(session_id)

        recommendations = [
            self._enrich_recommendation(item, state, rank)
            for rank, item in enumerate(response["recommendations"], start=1)
        ]
        return {
            "message": response["message"],
            "ask_attribute": response["ask_attribute"],
            "recommendations": recommendations,
            "state": state,
        }

    def _enrich_recommendation(self, item: dict, state: dict, rank: int) -> dict:
        product = self.products.get(str(item["parent_asin"]), {})
        product_text = " ".join(
            str(value)
            for value in (
                product.get("title", ""),
                product.get("features", ""),
                product.get("description", ""),
                product.get("details", ""),
            )
        ).lower()

        evidence: list[str] = []
        for hypothesis in state["hidden_need_hypotheses"]:
            matching_terms = [
                term for term in search_terms(hypothesis["value"])
                if term in product_text
            ]
            if matching_terms:
                evidence.append(matching_terms[0])
        if not evidence:
            for constraint in state["explicit_constraints"]:
                matching_terms = [term for term in search_terms(constraint) if term in product_text]
                if matching_terms:
                    evidence.append(matching_terms[0])
        evidence = list(dict.fromkeys(evidence))[:3]

        price = product.get("price")
        return {
            "rank": rank,
            "parent_asin": item["parent_asin"],
            "title": product.get("title") or "Untitled product",
            "store": product.get("store") or "Independent seller",
            "price": f"${float(price):.2f}" if price not in (None, "") else "Price unavailable",
            "average_rating": float(product.get("average_rating") or 0),
            "rating_number": int(product.get("rating_number") or 0),
            "evidence": evidence,
        }


class RequestHandler(BaseHTTPRequestHandler):
    app: NeedDecoderApplication

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        route = urlparse(self.path).path
        if route == "/api/health":
            self._write_json({"status": "ok", "products": len(self.app.products)})
            return
        if route == "/":
            route = "/index.html"
        requested = (WEB_ROOT / route.lstrip("/")).resolve()
        if WEB_ROOT not in requested.parents or not requested.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type, _ = mimetypes.guess_type(requested.name)
        body = requested.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        route = urlparse(self.path).path
        try:
            payload = self._read_json()
            if route == "/api/reset":
                session_id = str(payload.get("session_id") or "web-demo")
                self._write_json(self.app.reset(session_id))
                return
            if route == "/api/chat":
                message = str(payload.get("message") or "").strip()
                if not message:
                    self._write_json({"error": "Message cannot be empty."}, HTTPStatus.BAD_REQUEST)
                    return
                result = self.app.chat(
                    session_id=str(payload.get("session_id") or "web-demo"),
                    message=message,
                    turn=max(1, int(payload.get("turn") or 1)),
                    top_k=min(6, max(1, int(payload.get("top_k") or 3))),
                )
                self._write_json(result)
                return
            self._write_json({"error": "Unknown endpoint."}, HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError) as error:
            self._write_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:  # Keep the demo responsive and show actionable errors.
            self._write_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def _write_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Need Decoder web demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(os.environ.get("NEED_DECODER_CATALOG", DEFAULT_CATALOG)),
    )
    args = parser.parse_args()
    if not args.catalog.is_file():
        raise SystemExit(
            f"Catalog not found at {args.catalog}. Download it as described in data/README.md."
        )

    print(f"Building local search index from {args.catalog} ...", flush=True)
    app = NeedDecoderApplication(args.catalog)
    RequestHandler.app = app
    server = HTTPServer((args.host, args.port), RequestHandler)
    print(f"Need Decoder is running at http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
