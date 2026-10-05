"""Minimal hybrid-memory agent: Qdrant episodes + online profile features."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models
from rank_bm25 import BM25Okapi


class ProfileStore(Protocol):
    def get(self, user_id: str) -> dict: ...


class DictProfileStore:
    """Offline fallback with the same shape as an online feature lookup."""

    def __init__(self) -> None:
        self.rows = {
            "u_001": {
                "topic_affinity": "cloud",
                "preferred_language": "vi",
                "reading_speed_wpm": 245,
                "queries_last_hour": 7,
            }
        }

    def get(self, user_id: str) -> dict:
        return self.rows.get(user_id, {
            "topic_affinity": "unknown",
            "preferred_language": "vi",
            "reading_speed_wpm": 220,
            "queries_last_hour": 0,
        })


class FeastProfileStore:
    """Thin adapter around the feature views created by NB4."""

    FEATURES = [
        "user_profile_features:topic_affinity",
        "user_profile_features:preferred_language",
        "user_profile_features:reading_speed_wpm",
        "query_velocity_features:queries_last_hour",
    ]

    def __init__(self, repo_path: Path) -> None:
        from feast import FeatureStore

        self.store = FeatureStore(repo_path=str(repo_path))

    def get(self, user_id: str) -> dict:
        raw = self.store.get_online_features(
            features=self.FEATURES,
            entity_rows=[{"user_id": user_id}],
        ).to_dict()
        return {key: values[0] for key, values in raw.items() if key != "user_id"}


@dataclass
class Memory:
    point_id: int
    user_id: str
    text: str


class HybridMemoryAgent:
    """Store episodes, retrieve with BM25 + vectors, then attach profile state."""

    COLLECTION = "bonus_hybrid_memory"

    def __init__(self, profile_store: ProfileStore | None = None) -> None:
        self.embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        self.client = QdrantClient(":memory:")
        self.client.create_collection(
            collection_name=self.COLLECTION,
            vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
        )
        self.profile_store = profile_store or self._default_profile_store()
        self.memories: list[Memory] = []

    @staticmethod
    def _default_profile_store() -> ProfileStore:
        repo = Path(__file__).resolve().parents[1] / "app" / "feast_repo"
        if not (repo / "registry.db").exists():
            return DictProfileStore()
        try:
            return FeastProfileStore(repo)
        except Exception:  # clean checkout before NB4: keep the demo runnable
            return DictProfileStore()

    @staticmethod
    def _chunks(text: str, max_words: int = 80) -> list[str]:
        """Small deterministic chunks; production would split on semantics."""
        paragraphs = [part.strip() for part in text.split("\n") if part.strip()]
        chunks: list[str] = []
        for paragraph in paragraphs or [text.strip()]:
            words = paragraph.split()
            chunks.extend(" ".join(words[i:i + max_words])
                          for i in range(0, len(words), max_words))
        return [chunk for chunk in chunks if chunk]

    def remember(self, text: str, user_id: str = "u_001") -> None:
        """Chunk, embed and upsert one episodic memory for this user."""
        for chunk in self._chunks(text):
            point_id = len(self.memories)
            vector = next(self.embedder.embed([chunk])).tolist()
            self.client.upsert(
                collection_name=self.COLLECTION,
                points=[models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"user_id": user_id, "text": chunk},
                )],
            )
            self.memories.append(Memory(point_id, user_id, chunk))

    def _hybrid(self, query: str, user_id: str, top_k: int = 3) -> list[str]:
        candidates = [memory for memory in self.memories if memory.user_id == user_id]
        if not candidates:
            return []

        bm25 = BM25Okapi([memory.text.lower().split() for memory in candidates])
        scores = bm25.get_scores(query.lower().split())
        keyword_ids = [candidates[i].point_id for i in
                       sorted(range(len(scores)), key=lambda i: -scores[i])[:10]]

        user_filter = models.Filter(must=[models.FieldCondition(
            key="user_id", match=models.MatchValue(value=user_id))])
        vector_hits = self.client.query_points(
            collection_name=self.COLLECTION,
            query=next(self.embedder.embed([query])).tolist(),
            query_filter=user_filter,
            limit=min(10, len(candidates)),
        ).points

        rrf: dict[int, float] = {}
        for ranking in (keyword_ids, [int(hit.id) for hit in vector_hits]):
            for rank, point_id in enumerate(ranking, start=1):
                rrf[point_id] = rrf.get(point_id, 0.0) + 1.0 / (60 + rank)
        winners = sorted(rrf, key=rrf.get, reverse=True)[:top_k]
        by_id = {memory.point_id: memory.text for memory in candidates}
        return [by_id[point_id] for point_id in winners]

    def recall(self, query: str, user_id: str = "u_001") -> str:
        """Return assembled profile, activity and top episodic memories."""
        profile = self.profile_store.get(user_id)
        memories = self._hybrid(query, user_id)
        rendered = "\n".join(f"  {i}. {text}" for i, text in enumerate(memories, 1))
        return (
            f"User {user_id}: language={profile.get('preferred_language')}, "
            f"topic_affinity={profile.get('topic_affinity')}, "
            f"reading_speed={profile.get('reading_speed_wpm')} wpm.\n"
            f"Recent activity: {profile.get('queries_last_hour')} queries in the last hour.\n"
            f"Top memories:\n{rendered or '  (none)'}"
        )
