from src.topic_clustering import cosine_similarity, UnionFind

def test_cosine_similarity():
    assert cosine_similarity([1, 0], [1, 0]) == 1.0

def test_union_find():
    uf = UnionFind(3)
    uf.union(0, 1)
    assert uf.find(0) == uf.find(1)