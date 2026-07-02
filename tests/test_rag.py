import pytest
from pathlib import Path
from nexus.core.rag import chunk_text, cosine_similarity, keyword_match_score, CodebaseRAG

def test_chunk_text():
    text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    assert len(chunks) > 0
    assert chunks[0]["start_line"] == 1
    assert "Line 1" in chunks[0]["text"]

def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-6

    v3 = [0.0, 1.0, 0.0]
    assert abs(cosine_similarity(v1, v3)) < 1e-6

    v4 = [1.0, 1.0, 0.0]
    # Cosine of 45 deg = 0.7071
    assert abs(cosine_similarity(v1, v4) - 0.707106) < 1e-4

def test_keyword_match_score():
    text = "Python is a great programming language for AI development."
    score_python = keyword_match_score(text, "python")
    score_rust = keyword_match_score(text, "rust")
    assert score_python > 0.0
    assert score_rust == 0.0

def test_rag_indexing_and_search(tmp_path, monkeypatch):
    # Set up dummy codebase directory
    project_dir = tmp_path / "dummy_project"
    project_dir.mkdir()
    
    file1 = project_dir / "app.py"
    file1.write_text("import os\n\ndef main():\n    print('Hello World')\n", encoding="utf-8")
    
    file2 = project_dir / "utils.py"
    file2.write_text("def helper():\n    return 'useful helper'\n", encoding="utf-8")
    
    # Configure temporary sessions dir
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    monkeypatch.setattr("nexus.core.rag.SESSIONS_DIR", sessions_dir)
    
    rag = CodebaseRAG(str(project_dir))
    
    # Run text-only indexing (providing empty embeddings)
    # We pass empty provider and model to simulate offline/fallback behavior
    rag.index_project(provider="", model="", host="", api_key="")
    
    stats = rag.get_index_stats()
    assert stats["total_files"] == 2
    assert stats["total_chunks"] >= 2
    
    # Perform search using keyword fallback
    results = rag.search("helper", top_k=2)
    assert len(results) > 0
    assert results[0]["file"] == "utils.py"
    assert "useful helper" in results[0]["text"]
