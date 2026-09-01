from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from need_decoder.state import ConversationState
from need_decoder.text import PricePreference, normalized_text, parse_price_preference, search_terms

PRICE_QUERY_WORDS = {
    "above", "around", "at", "below", "between", "budget", "cost", "least",
    "less", "max", "maximum", "min", "minimum", "more", "over", "price",
    "spend", "than", "under", "up",
}


@dataclass
class Candidate:
    parent_asin: str
    title: str
    categories: str
    features: str
    details: str
    store: str
    description: str
    price: float | None
    average_rating: float
    rating_number: int
    source_rank: int

    @property
    def combined_text(self) -> str:
        return " ".join((self.title, self.categories, self.features, self.details, self.store, self.description)).lower()


class CatalogSearch:
    """In-memory FTS retrieval followed by deterministic, field-aware reranking."""

    def __init__(self, catalog_path: str | Path) -> None:
        self.catalog_path = Path(catalog_path)
        self.connection = sqlite3.connect(":memory:")
        self.document_count = 0
        self._document_frequency: dict[str, int] = {}
        self._field_term_cache: dict[str, dict[str, set[str]]] = {}
        self._result_cache: dict[tuple, list[dict]] = {}
        self._build_index()

    def _build_index(self) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            "CREATE VIRTUAL TABLE products USING fts5("
            "parent_asin UNINDEXED, title, categories, features, details, store, description, "
            "price UNINDEXED, average_rating UNINDEXED, rating_number UNINDEXED, "
            "tokenize='unicode61 remove_diacritics 2')"
        )
        batch: list[tuple] = []
        with self.catalog_path.open(encoding="utf-8") as catalog:
            for line in catalog:
                try:
                    product = json.loads(line)
                except json.JSONDecodeError:
                    # Public data dumps can end with a partially downloaded row.
                    # One bad record should not make the entire catalogue unusable.
                    continue
                batch.append(
                    (
                        str(product["parent_asin"]),
                        normalized_text(product.get("title")),
                        normalized_text(product.get("categories")),
                        normalized_text(product.get("features")),
                        normalized_text(product.get("details")),
                        normalized_text(product.get("store")),
                        normalized_text(product.get("description")),
                        _numeric_price(product.get("price")),
                        float(product.get("average_rating") or 0),
                        int(product.get("rating_number") or 0),
                    )
                )
                if len(batch) == 1000:
                    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
                    self.document_count += len(batch)
                    batch.clear()
        if batch:
            cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
            self.document_count += len(batch)
        cursor.execute("CREATE VIRTUAL TABLE product_terms USING fts5vocab(products, 'row')")
        self.connection.commit()

    def search(self, state: ConversationState, limit: int = 10) -> list[dict]:
        cache_key = (
            state.intent,
            state.category,
            tuple(state.constraints),
            tuple((item.attribute, item.value, item.confidence) for item in state.hypotheses),
            tuple(sorted(state.excluded_terms)),
            state.price_preference,
        )
        cached = self._result_cache.get(cache_key)
        if cached is not None:
            return [dict(item) for item in cached[:limit]]

        category_terms = search_terms(state.category or "")
        explicit_terms: list[str] = []
        seen_explicit_terms: set[str] = set()
        for constraint in state.constraints:
            terms = search_terms(_constraint_search_text(constraint))
            price_preference = parse_price_preference(constraint)
            price_tokens: set[str] = set()
            if price_preference:
                price_tokens = {
                    token
                    for value in (
                        price_preference.target,
                        price_preference.minimum,
                        price_preference.maximum,
                    )
                    if value is not None
                    for token in search_terms(str(value))
                }
            for term in terms:
                if (
                    term in state.excluded_terms
                    or term in PRICE_QUERY_WORDS
                    or term in price_tokens
                    or term in seen_explicit_terms
                ):
                    continue
                seen_explicit_terms.add(term)
                explicit_terms.append(term)
        hypothesis_terms = search_terms(" ".join(item.value for item in state.hypotheses))
        candidates = self._candidate_pool(
            category_terms,
            explicit_terms,
            hypothesis_terms,
            intent=state.intent,
        )
        if not candidates:
            return []

        term_idf = {
            term: self._idf(term)
            for term in dict.fromkeys(category_terms + explicit_terms + hypothesis_terms)
        }
        ranked = sorted(
            candidates.values(),
            key=lambda item: self._score_candidate(
                item,
                state,
                category_terms,
                explicit_terms,
                hypothesis_terms,
                term_idf,
            ),
            reverse=True,
        )
        result = [{"parent_asin": item.parent_asin} for item in ranked[:10]]
        self._result_cache[cache_key] = result
        return [dict(item) for item in result[:limit]]

    def _candidate_pool(
        self,
        category_terms: list[str],
        explicit_terms: list[str],
        hypothesis_terms: list[str],
        intent: str,
    ) -> dict[str, Candidate]:
        candidates: dict[str, Candidate] = {}
        root_category_terms = {"clothing", "shoes", "jewelry"}
        specific_category_terms = [term for term in category_terms if term not in root_category_terms]
        if specific_category_terms:
            category_query = " AND ".join(
                f"categories:{_quoted(term)}" for term in specific_category_terms[:8]
            )
        else:
            category_query = " AND ".join(
                f"title:{_quoted(term)}" for term in category_terms[:8]
            )
        if intent == "buying":
            evidence_terms = list(dict.fromkeys(explicit_terms + hypothesis_terms))[:40]
            combined_limit, category_limit, evidence_limit = 1600, 4500, 1200
        else:
            # Browsing keeps a wider pool and lets contextual hypotheses lead
            # the evidence route. A direct requirement moves the state to the
            # higher-precision buying route on the next response.
            evidence_terms = list(dict.fromkeys(hypothesis_terms + explicit_terms))[:40]
            combined_limit, category_limit, evidence_limit = 2400, 4500, 1800
        evidence_query = " OR ".join(_quoted(term) for term in evidence_terms)

        queries: list[tuple[str, int]] = []
        if category_query and evidence_query:
            queries.append((f"({category_query}) AND ({evidence_query})", combined_limit))
        if category_query:
            queries.append((category_query, category_limit))
        if evidence_query and not category_query:
            queries.append((evidence_query, evidence_limit))

        source_rank = 0
        for expression, row_limit in queries:
            try:
                rows = self.connection.execute(
                    "SELECT parent_asin, title, categories, features, details, store, description, "
                    "price, average_rating, rating_number FROM products WHERE products MATCH ? "
                    "ORDER BY bm25(products, 0.0, 7.0, 5.0, 3.0, 2.0, 1.5, 1.0, 0.0, 0.0, 0.0) LIMIT ?",
                    (expression, row_limit),
                ).fetchall()
            except sqlite3.OperationalError:
                continue
            for row in rows:
                parent_asin = str(row[0])
                if parent_asin in candidates:
                    continue
                candidates[parent_asin] = Candidate(
                    parent_asin=parent_asin,
                    title=str(row[1]), categories=str(row[2]), features=str(row[3]),
                    details=str(row[4]), store=str(row[5]), description=str(row[6]),
                    price=float(row[7]) if row[7] not in (None, "") else None,
                    average_rating=float(row[8] or 0), rating_number=int(float(row[9] or 0)),
                    source_rank=source_rank,
                )
                source_rank += 1
        return candidates

    def _score_candidate(
        self,
        candidate: Candidate,
        state: ConversationState,
        category_terms: list[str],
        explicit_terms: list[str],
        hypothesis_terms: list[str],
        term_idf: dict[str, float],
    ) -> float:
        field_terms = self._field_term_cache.get(candidate.parent_asin)
        if field_terms is None:
            field_terms = {
                "title": set(search_terms(candidate.title)),
                "categories": set(search_terms(candidate.categories)),
                "features": set(search_terms(candidate.features)),
                "details": set(search_terms(candidate.details)),
                "store": set(search_terms(candidate.store)),
                "description": set(search_terms(candidate.description)),
            }
            self._field_term_cache[candidate.parent_asin] = field_terms
        field_weights = {
            "title": 4.2, "categories": 3.2, "features": 4.2,
            "details": 2.4, "store": 2.0, "description": 1.2,
        }

        score = 0.0
        for term in category_terms:
            if term in field_terms["categories"]:
                score += (0.4 if term in {"clothing", "shoes", "jewelry"} else 4.0) * term_idf[term]
            if term in field_terms["title"]:
                score += 1.0 * term_idf[term]

        for term in explicit_terms:
            best_field_weight = max(
                (weight for field, weight in field_weights.items() if term in field_terms[field]),
                default=0.0,
            )
            score += best_field_weight * term_idf[term]

        hypothesis_confidence = {
            term: max(
                (item.confidence for item in state.hypotheses if term in search_terms(item.value)),
                default=0.0,
            )
            for term in hypothesis_terms
        }
        for term in hypothesis_terms:
            best_field_weight = max(
                (weight for field, weight in field_weights.items() if term in field_terms[field]),
                default=0.0,
            )
            score += 0.28 * hypothesis_confidence[term] * best_field_weight * term_idf[term]

        combined = candidate.combined_text
        for constraint in state.constraints:
            if parse_price_preference(constraint):
                continue
            normalized_constraint = " ".join(search_terms(_constraint_search_text(constraint)))
            if normalized_constraint and normalized_constraint in " ".join(search_terms(combined)):
                score += 14.0

        combined_terms = set(search_terms(combined))
        for term in state.excluded_terms:
            if term in combined_terms:
                score -= 12.0 * term_idf.get(term, self._idf(term))

        score += _price_score(candidate.price, state.price_preference)

        # Source rank and log-scaled review count are fallback priors. Explicit
        # customer evidence still contributes most of the score.
        score += 0.6 / (1.0 + candidate.source_rank)
        score += 1.30 * math.log1p(candidate.rating_number)
        score += 0.08 * candidate.average_rating
        return score

    def _idf(self, term: str) -> float:
        if term not in self._document_frequency:
            row = self.connection.execute(
                "SELECT doc FROM product_terms WHERE term = ?",
                (term,),
            ).fetchone()
            self._document_frequency[term] = int(row[0]) if row else 0
        frequency = self._document_frequency[term]
        return math.log((self.document_count + 1) / (frequency + 1)) + 1.0


def _quoted(term: str) -> str:
    return '"' + term.replace('"', '""') + '"'


def _price_score(price: float | None, preference: PricePreference | None) -> float:
    if preference is None or price is None:
        return 0.0
    if preference.target is not None:
        difference = abs(price - preference.target)
        tolerance = max(2.0, preference.target * 0.10)
        return 18.0 * max(0.0, 1.0 - difference / tolerance)

    score = 0.0
    if preference.minimum is not None:
        score += 7.0 if price >= preference.minimum else -min(18.0, preference.minimum - price)
    if preference.maximum is not None:
        score += 7.0 if price <= preference.maximum else -min(18.0, price - preference.maximum)
    return score


def _numeric_price(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _constraint_search_text(constraint: str) -> str:
    return re.sub(
        r"\b(?:brand|color|department|feature|material|size|style|use case)\s*:\s*",
        "",
        constraint,
        flags=re.IGNORECASE,
    )
