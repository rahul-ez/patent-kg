"""Shared public-patent vectors; no private queries or analysis outputs are cached.

Reuse FAISS vectors for identical encoder inputs, then a bounded memory/disk
cache, and batch only the remaining texts. Publication IDs stay distinct.
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
from collections import OrderedDict
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from time import time

import faiss
import numpy as np

logger = logging.getLogger(__name__)
TEXT_VERSION = "title-dot-abstract-raw-l2-v1"


def patent_text(row: dict) -> str:
    return f"{row.get('title') or ''}. {row.get('abstract') or ''}".strip()


def _key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class PatentEmbeddings:
    def __init__(self, index, metadata: dict, patent_rows: dict, model, *,
                 namespace: str = "", cache_path: Path | None = None,
                 memory_limit: int = 4096, disk_limit: int = 20000, batch_size: int = 32):
        self.index = index
        self.model = model
        self.patent_rows = patent_rows
        self.namespace = _key(f"{TEXT_VERSION}:{namespace}:{index.d}")
        self.cache_path = cache_path
        self.memory_limit = max(0, memory_limit)
        self.disk_limit = max(0, disk_limit)
        self.batch_size = max(1, batch_size)
        self._memory = OrderedDict()
        # Serialize population across request threads so identical misses encode once.
        self._lock = RLock()
        self._row_by_id = {pid: int(row) for row, pid in metadata.items() if str(row).isdigit()}
        self._row_by_text = {}
        for pid, row_index in self._row_by_id.items():
            text = patent_text(patent_rows.get(pid, {}))
            if text != ".":
                self._row_by_text.setdefault(_key(text), row_index)
        if self.cache_path is not None and self.disk_limit:
            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                with self._connect() as connection:
                    connection.execute("""CREATE TABLE IF NOT EXISTS vectors (
                        namespace TEXT NOT NULL, content_key TEXT NOT NULL,
                        vector BLOB NOT NULL, used_at REAL NOT NULL,
                        PRIMARY KEY (namespace, content_key))""")
                    connection.execute("CREATE INDEX IF NOT EXISTS vectors_used ON vectors(used_at)")
            except (OSError, sqlite3.Error) as exc:
                self._disable_disk(exc)
        else:
            self.cache_path = None

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.cache_path, timeout=1)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _disable_disk(self, exc):
        logger.warning("Public embedding disk cache unavailable; using memory/batching: %s", exc)
        self.cache_path = None

    def _valid(self, vector):
        return vector.shape == (self.index.d,) and bool(np.isfinite(vector).all())

    def _remember(self, key, vector):
        if self.memory_limit:
            self._memory[key] = vector.copy()
            self._memory.move_to_end(key)
            while len(self._memory) > self.memory_limit:
                self._memory.popitem(last=False)

    def _read_disk(self, keys):
        if self.cache_path is None or not keys:
            return {}
        found = {}
        try:
            with self._connect() as connection:
                for start in range(0, len(keys), 400):
                    chunk = keys[start:start + 400]
                    rows = connection.execute(
                        f"SELECT content_key, vector FROM vectors WHERE namespace=? AND content_key IN ({','.join('?' for _ in chunk)})",
                        [self.namespace, *chunk],
                    )
                    for key, blob in rows:
                        if len(blob) != self.index.d * 4:
                            continue
                        vector = np.frombuffer(blob, dtype="<f4").copy()
                        if self._valid(vector):
                            found[key] = vector
                connection.executemany("UPDATE vectors SET used_at=? WHERE namespace=? AND content_key=?",
                                       [(time(), self.namespace, key) for key in found])
        except (OSError, sqlite3.Error) as exc:
            self._disable_disk(exc)
        return found

    def _write_disk(self, vectors):
        if self.cache_path is None or not vectors:
            return
        try:
            with self._connect() as connection:
                connection.executemany("INSERT OR REPLACE INTO vectors VALUES (?, ?, ?, ?)", [
                    (self.namespace, key, vector.astype("<f4").tobytes(), time())
                    for key, vector in vectors.items()
                ])
                # Bound entries across ALL model/corpus versions, not just this one.
                connection.execute("""DELETE FROM vectors WHERE rowid IN (
                    SELECT rowid FROM vectors ORDER BY used_at DESC LIMIT -1 OFFSET ?)
                    """, (self.disk_limit,))
        except (OSError, sqlite3.Error) as exc:
            self._disable_disk(exc)

    def get_many(self, records: list[dict]) -> np.ndarray:
        """Return aligned vectors. Unknown records use request-local batching only.

        Only canonical public metadata can populate shared memory/disk entries;
        caller-supplied text for unknown IDs never enters either shared cache.
        Copies are returned, so scoring cannot mutate cached vectors.
        """
        if not records:
            return np.empty((0, self.index.d), dtype=np.float32)
        with self._lock:
            resolved = {}
            texts = {}
            keys = []
            public_keys = set()
            reconstructed = 0
            for record in records:
                pid = record.get("patent_id")
                public = pid in self.patent_rows
                row = self.patent_rows[pid] if public else record
                text = patent_text(row)
                key = _key(text)
                keys.append(key)
                if public:
                    public_keys.add(key)
                if key in resolved:
                    continue
                if text == ".":
                    resolved[key] = np.zeros(self.index.d, dtype=np.float32)
                    continue
                # Reconstruct indexed IDs and exact-text aliases without re-encoding.
                row_index = self._row_by_id.get(pid) if public else None
                if public and row_index is None:
                    row_index = self._row_by_text.get(key)
                if row_index is not None:
                    try:
                        vector = np.asarray(self.index.reconstruct(row_index), dtype=np.float32)
                        if self._valid(vector):
                            resolved[key] = vector
                            reconstructed += 1
                            continue
                    except Exception:
                        pass  # Some FAISS index types do not support reconstruct.
                if public and key in self._memory:
                    resolved[key] = self._memory[key]
                    self._memory.move_to_end(key)
                else:
                    texts[key] = text

            disk = self._read_disk([key for key in texts if key in public_keys])
            resolved.update(disk)
            for key, vector in disk.items():
                self._remember(key, vector)
            missing = [key for key in texts if key not in resolved]
            # Chunk here as well as in encode: peak intermediates stay bounded.
            for start in range(0, len(missing), self.batch_size):
                chunk = missing[start:start + self.batch_size]
                vectors = np.ascontiguousarray(self.model.encode(
                    [texts[key] for key in chunk], batch_size=self.batch_size,
                    convert_to_numpy=True, show_progress_bar=False,
                ), dtype=np.float32)
                if vectors.shape != (len(chunk), self.index.d) or not np.isfinite(vectors).all():
                    raise ValueError("Patent encoder returned invalid vectors.")
                faiss.normalize_L2(vectors)
                persistent = {}
                for key, vector in zip(chunk, vectors):
                    resolved[key] = vector
                    if key in public_keys:
                        self._remember(key, vector)
                        persistent[key] = vector
                self._write_disk(persistent)
            logger.info("Patent vectors: requested=%d, FAISS texts=%d, disk hits=%d, encoded texts=%d",
                        len(records), reconstructed, len(disk), len(missing))
            return np.stack([resolved[key] for key in keys]).astype(np.float32)
