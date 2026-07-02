import os
import re
import json
import hashlib
from pathlib import Path
import requests
from .config import SETTINGS, SESSIONS_DIR

# File extensions we care about
TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".md", ".txt",
    ".rs", ".go", ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".sh", ".bat",
    ".yaml", ".yml", ".toml", ".ini", ".properties"
}

# Directories to ignore during crawling
IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", "venv", ".venv", "env", ".env",
    "dist", "build", "target", ".idea", ".vscode", ".pytest_cache", ".mypy_cache"
}

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """
    Split text into chunks of roughly chunk_size characters, preserving line boundaries
    and providing an overlap.
    Returns: list of dicts: {"text": str, "start_line": int, "end_line": int}
    """
    lines = text.splitlines(keepends=True)
    chunks = []
    current_chunk = []
    current_len = 0
    start_line = 1

    for i, line in enumerate(lines):
        line_num = i + 1
        current_chunk.append(line)
        current_len += len(line)

        if current_len >= chunk_size:
            chunk_text_str = "".join(current_chunk)
            chunks.append({
                "text": chunk_text_str,
                "start_line": start_line,
                "end_line": line_num
            })
            # Handle overlap: keep last few lines that sum up to less than overlap
            overlap_lines = []
            overlap_len = 0
            for ol_line in reversed(current_chunk):
                if overlap_len + len(ol_line) > overlap:
                    break
                overlap_lines.insert(0, ol_line)
                overlap_len += len(ol_line)

            current_chunk = overlap_lines
            current_len = overlap_len
            start_line = line_num - len(overlap_lines) + 1

    if current_chunk:
        chunk_text_str = "".join(current_chunk)
        chunks.append({
            "text": chunk_text_str,
            "start_line": start_line,
            "end_line": len(lines)
        })

    return chunks


def get_embeddings_batch(texts: list, provider: str, model: str, host: str, api_key: str) -> list:
    """
    Fetch embeddings for a list of texts using the selected provider.
    Returns list of float lists.
    """
    if not texts:
        return []

    if provider == "ollama":
        url = f"{host or 'http://localhost:11434'}/api/embed"
        payload = {
            "model": model or "nomic-embed-text",
            "input": texts
        }
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["embeddings"]
    elif provider in ("openai", "openai_compatible"):
        base_url = SETTINGS.get("openai_base_url", "https://api.openai.com/v1") if provider == "openai" else host
        url = f"{base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model or "text-embedding-3-small",
            "input": texts
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        # OpenAI returns {"data": [{"embedding": [...], "index": 0}, ...]}
        data = resp.json()["data"]
        data_sorted = sorted(data, key=lambda x: x["index"])
        return [item["embedding"] for item in data_sorted]
    else:
        raise ValueError(f"Embedding provider '{provider}' is not supported.")


def cosine_similarity(v1: list, v2: list) -> float:
    """Compute cosine similarity of two float vectors in pure Python."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(x * y for x, y in zip(v1, v2))
    norm_v1 = sum(x * x for x in v1) ** 0.5
    norm_v2 = sum(x * x for x in v2) ** 0.5
    if not norm_v1 or not norm_v2:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)


def keyword_match_score(text: str, query: str) -> float:
    """Rank text chunk by matching terms from query."""
    query_words = set(re.findall(r'\w+', query.lower()))
    if not query_words:
        return 0.0
    text_words = re.findall(r'\w+', text.lower())
    score = 0.0
    for qw in query_words:
        count = text_words.count(qw)
        if count > 0:
            # Base match + term frequency incentive
            score += 1.0 + 0.3 * count
    return score


class CodebaseRAG:
    """
    RAG Search and QA system for a specific project folder.
    Stores index inside SESSIONS_DIR / "rag" / <project_hash>.json
    """
    def __init__(self, project_path: str):
        self.project_path = str(Path(project_path).resolve())
        self.rag_dir = SESSIONS_DIR / "rag"
        self.rag_dir.mkdir(parents=True, exist_ok=True)
        
        # Unique hash based on project path
        path_hash = hashlib.md5(self.project_path.encode('utf-8')).hexdigest()
        self.index_file = self.rag_dir / f"index_{path_hash}.json"
        
        self.index_data = {
            "project_path": self.project_path,
            "provider": "",
            "model": "",
            "files": {}  # relative_path -> {mtime, hash, chunks: [{text, start_line, end_line, embedding}]}
        }
        self.load_index()

    def load_index(self):
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self.index_data.update(json.load(f))
            except Exception:
                pass

    def save_index(self):
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(self.index_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def clear_index(self):
        self.index_data["files"] = {}
        if self.index_file.exists():
            try:
                self.index_file.unlink()
            except Exception:
                pass

    def get_index_stats(self) -> dict:
        total_files = len(self.index_data["files"])
        total_chunks = sum(len(finfo.get("chunks", [])) for finfo in self.index_data["files"].values())
        return {
            "total_files": total_files,
            "total_chunks": total_chunks,
            "model": self.index_data.get("model", "None"),
            "provider": self.index_data.get("provider", "None")
        }

    def index_project(self, provider: str, model: str, host: str, api_key: str, progress_cb=None, log_cb=None):
        """
        Scan codebase and build/update embedding index.
        """
        def log(msg, level="info"):
            if log_cb:
                log_cb(msg, level)
            else:
                print(f"[{level.upper()}] {msg}")

        # Update metadata
        self.index_data["provider"] = provider
        self.index_data["model"] = model

        proj_path = Path(self.project_path)
        if not proj_path.exists():
            log(f"Project path does not exist: {self.project_path}", "error")
            return

        # Crawl all files
        all_filepaths = []
        for root, dirs, files in os.walk(proj_path):
            # Ignore hidden or blacklisted folders
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
            
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in TEXT_EXTENSIONS:
                    all_filepaths.append(Path(root) / file)

        total_files = len(all_filepaths)
        log(f"Found {total_files} text/code files to analyze.", "info")

        # Track existing files to check for deletions later
        current_relative_paths = set()
        files_updated = 0
        chunks_indexed = 0

        # Step 1: Scan and identify modified/new files
        files_to_embed = []  # List of tuples (relative_path, absolute_path, list_of_chunks_to_embed)
        
        for idx, abs_path in enumerate(all_filepaths):
            if progress_cb:
                progress_cb(int((idx / max(total_files, 1)) * 50)) # first 50% for scanning/chunking

            rel_path = str(abs_path.relative_to(proj_path))
            current_relative_paths.add(rel_path)

            try:
                stat = abs_path.stat()
                mtime = stat.st_mtime
                
                # Check if file has changed
                existing_info = self.index_data["files"].get(rel_path)
                if existing_info and existing_info.get("mtime") == mtime:
                    # File unchanged
                    chunks_indexed += len(existing_info.get("chunks", []))
                    continue

                # Read and chunk
                text = abs_path.read_text(encoding="utf-8", errors="replace")
                
                # Simple file hashing
                fhash = hashlib.md5(text.encode("utf-8")).hexdigest()
                if existing_info and existing_info.get("hash") == fhash:
                    # Content is identical, just update timestamp
                    existing_info["mtime"] = mtime
                    chunks_indexed += len(existing_info.get("chunks", []))
                    continue

                chunks = chunk_text(text, 
                                    chunk_size=SETTINGS.get("rag_chunk_size", 1000), 
                                    overlap=SETTINGS.get("rag_chunk_overlap", 200))
                
                if chunks:
                    files_to_embed.append((rel_path, abs_path, chunks, mtime, fhash))
                else:
                    # Empty file
                    self.index_data["files"][rel_path] = {
                        "mtime": mtime,
                        "hash": fhash,
                        "chunks": []
                    }
            except Exception as e:
                log(f"Failed to process {rel_path}: {e}", "warn")

        # Step 2: Request embeddings for chunks in batch
        flat_chunks = []
        for rel_path, abs_path, chunks, mtime, fhash in files_to_embed:
            for chunk in chunks:
                flat_chunks.append((rel_path, chunk))

        total_chunks_to_embed = len(flat_chunks)
        if total_chunks_to_embed > 0:
            log(f"Generating embeddings for {total_chunks_to_embed} chunks across {len(files_to_embed)} modified/new files...", "info")
            
            # Batch embeddings in groups of 16 to avoid payload limits
            batch_size = 16
            embeddings = []
            
            for i in range(0, total_chunks_to_embed, batch_size):
                if progress_cb:
                    # Remaining 50% for embeddings
                    progress_idx = 50 + int((i / total_chunks_to_embed) * 50)
                    progress_cb(progress_idx)
                
                batch = flat_chunks[i:i+batch_size]
                batch_texts = [item[1]["text"] for item in batch]
                try:
                    batch_embs = get_embeddings_batch(batch_texts, provider, model, host, api_key)
                    embeddings.extend(batch_embs)
                except Exception as e:
                    log(f"Failed to generate embeddings for batch {i//batch_size + 1}: {e}. Falling back to text-only indexing.", "error")
                    # Fill with empty lists so we can still save text chunk data
                    embeddings.extend([[] for _ in batch])

            # Re-assemble embeddings back into their files
            embedding_idx = 0
            file_chunks_map = {rel_path: [] for rel_path, _, _, _, _ in files_to_embed}
            
            for rel_path, chunk in flat_chunks:
                emb = embeddings[embedding_idx] if embedding_idx < len(embeddings) else []
                chunk["embedding"] = emb
                file_chunks_map[rel_path].append(chunk)
                embedding_idx += 1

            # Update index dict
            for rel_path, abs_path, chunks, mtime, fhash in files_to_embed:
                self.index_data["files"][rel_path] = {
                    "mtime": mtime,
                    "hash": fhash,
                    "chunks": file_chunks_map[rel_path]
                }
                files_updated += 1
                chunks_indexed += len(file_chunks_map[rel_path])

        # Step 3: Remove deleted files from the index
        indexed_paths = list(self.index_data["files"].keys())
        deleted_count = 0
        for rel_path in indexed_paths:
            if rel_path not in current_relative_paths:
                del self.index_data["files"][rel_path]
                deleted_count += 1

        self.save_index()
        log(f"Indexing complete! Updated: {files_updated} file(s). Deleted: {deleted_count} file(s). Total indexed chunks: {chunks_indexed}.", "success")
        if progress_cb:
            progress_cb(100)

    def search(self, query: str, top_k: int = 5, provider: str = "", model: str = "", host: str = "", api_key: str = "") -> list:
        """
        Search for relevant chunks using hybrid vector + keyword matching.
        """
        if not query.strip():
            return []

        # Get embedding of query if provider configured
        query_emb = None
        if provider and model:
            try:
                query_embs = get_embeddings_batch([query], provider, model, host, api_key)
                if query_embs:
                    query_emb = query_embs[0]
            except Exception:
                # Silently fall back to keyword search on error
                pass

        results = []
        for rel_path, finfo in self.index_data["files"].items():
            for idx, chunk in enumerate(finfo.get("chunks", [])):
                score = 0.0
                
                # 1. Cosine similarity score (Vector search)
                emb_sim = 0.0
                if query_emb and chunk.get("embedding"):
                    emb_sim = cosine_similarity(query_emb, chunk["embedding"])
                
                # 2. Keyword frequency score (Text search)
                text_score = keyword_match_score(chunk["text"], query)
                
                # Normalize keyword score slightly
                normalized_text_score = min(text_score / 15.0, 1.0)
                
                # Combined score
                if query_emb:
                    score = 0.7 * emb_sim + 0.3 * normalized_text_score
                else:
                    score = normalized_text_score

                if score > 0.05:  # Relevance threshold
                    results.append({
                        "file": rel_path,
                        "start_line": chunk["start_line"],
                        "end_line": chunk["end_line"],
                        "text": chunk["text"],
                        "score": score,
                        "vector_score": emb_sim,
                        "keyword_score": text_score
                    })

        # Sort by overall score descending
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        return results[:top_k]
