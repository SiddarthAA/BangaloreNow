import os
import faiss
import numpy as np
import pickle
from google.cloud import storage
from sentence_transformers import SentenceTransformer

import logging

class Logger:
    def __init__(self, name: str, level=logging.INFO):
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        )
        self.logger = logging.getLogger(name)

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def critical(self, message: str):
        self.logger.critical(message)
logger = Logger("blrnow : index")

class FaissIndexManager:
    def __init__(
        self,
        bucket_name: str = "run-bucket",
        gcs_prefix: str = "vector-map",
        index_file: str = "store.index",
        dim: int = 384  
    ):
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.dim = dim

        self.bucket_name = bucket_name
        self.gcs_prefix = gcs_prefix.strip("/")

        self.index_file = f"{self.gcs_prefix}/{index_file}"

        self.local_index_path = f"/tmp/{index_file}"

        self.index = None
        self.client = storage.Client()

    def _download_from_gcs(self):
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(self.index_file)

        if blob.exists(self.client):
            blob.download_to_filename(self.local_index_path)
            logging.info(f"Downloaded index from GCS: {self.index_file}")
            return True
        else:
            logging.warning(f"No index found at gs://{self.bucket_name}/{self.index_file}")
            return False

    def _upload_to_gcs(self):
        bucket = self.client.bucket(self.bucket_name)
        bucket.blob(self.index_file).upload_from_filename(self.local_index_path)
        logging.info(f"Uploaded index to gs://{self.bucket_name}/{self.gcs_prefix}/")

    def create_new_index(self):
        self.index = faiss.IndexFlatIP(self.dim)
        logging.info(f"Created new FAISS index with dim={self.dim}")

    def load_index(self):
        found = self._download_from_gcs()

        if found and os.path.exists(self.local_index_path):
            self.index = faiss.read_index(self.local_index_path)
            logging.info("Loaded FAISS index from local file")
        else:
            self.create_new_index()

    def save_index(self):
        if self.index is None:
            logging.error("No index to save.")
            return

        faiss.write_index(self.index, self.local_index_path)
        self._upload_to_gcs()

    def embed(self, text: str) -> np.ndarray:
        vector = self.embedder.encode([text], normalize_embeddings=True)
        return np.array(vector, dtype="float32")

    def add(self, text: str):
        if self.index is None:
            self.create_new_index()

        vector = self.embed(text)
        self.index.add(vector)
        logging.info("Added vector to index")

    def search(self, text: str, k: int = 1, threshold: float = 0.75) -> bool:
        if self.index is None or self.index.ntotal == 0:
            return False

        vector = self.embed(text)
        distances, indices = self.index.search(vector, k)

        for score in distances[0]:
            if score >= threshold:
                return True
        return False