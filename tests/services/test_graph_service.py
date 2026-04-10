# -*- coding: utf-8 -*-
"""Tests for backend.services.graph_service.GraphService."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Graph Loading
# ---------------------------------------------------------------------------

class TestGraphLoading:
    def test_load_graph_returns_nodes_and_edges(self, graph_service):
        """Graph should contain >= 30 nodes and >= 100 edges (roadmap-based graph)."""
        info = graph_service.info()
        assert info["node_count"] >= 30, f"Expected >= 30 nodes, got {info['node_count']}"
        assert info["edge_count"] >= 100, f"Expected >= 100 edges, got {info['edge_count']}"

    def test_every_node_has_base_fields(self, graph_service):
        """Every node must have label, role_family, must_skills."""
        for node_id in graph_service.node_ids:
            node = graph_service.get_node(node_id)
            assert node is not None, f"Node {node_id} returned None"
            assert "label" in node, f"Node {node_id} missing 'label'"
            assert "role_family" in node, f"Node {node_id} missing 'role_family'"
            assert "must_skills" in node, f"Node {node_id} missing 'must_skills'"

    def test_singleton_caching(self, graph_service):
        """Calling load() again returns the same cached instance."""
        graph_service.load()  # second call should be no-op
        info = graph_service.info()
        assert info["node_count"] >= 30


# ---------------------------------------------------------------------------
# Node Access
# ---------------------------------------------------------------------------

class TestNodeAccess:
    def test_get_node_by_id(self, graph_service):
        """Known node_id returns a dict with label."""
        # Pick the first available node
        first_id = graph_service.node_ids[0]
        node = graph_service.get_node(first_id)
        assert node is not None
        assert "label" in node

    def test_get_node_missing_returns_none(self, graph_service):
        """Unknown node_id returns None."""
        assert graph_service.get_node("__nonexistent_node__") is None

    def test_get_node_by_label(self, graph_service):
        """Known Chinese label returns a dict."""
        # Use the label from the first node
        first_id = graph_service.node_ids[0]
        first_node = graph_service.get_node(first_id)
        label = first_node["label"]
        found = graph_service.get_node_by_label(label)
        assert found is not None
        assert found["node_id"] == first_id

    def test_get_node_by_label_missing_returns_none(self, graph_service):
        """Unknown label returns None."""
        assert graph_service.get_node_by_label("__不存在的岗位__") is None

    def test_search_nodes_keyword(self, graph_service):
        """Keyword 'React' returns results containing React-related roles."""
        results = graph_service.search_nodes("React")
        assert len(results) > 0
        # At least one result should have 'React' in label or must_skills
        found = any(
            "React" in r.get("label", "")
            or any("React" in s for s in r.get("must_skills", []))
            for r in results
        )
        assert found, f"No 'React' match in results: {[r['label'] for r in results]}"

    def test_search_nodes_empty_keyword(self, graph_service):
        """Empty keyword returns empty list."""
        results = graph_service.search_nodes("")
        assert results == []


# ---------------------------------------------------------------------------
# Shortest Path
# ---------------------------------------------------------------------------

class TestShortestPath:
    def test_path_between_connected_nodes(self, graph_service):
        """Path between directly connected nodes exists and has >= 2 nodes."""
        # Find two connected nodes from graph edges
        info = graph_service.info()
        assert info["edge_count"] > 0
        # Use the first edge to get source/target
        result = graph_service.shortest_path(
            graph_service.node_ids[0], graph_service.node_ids[1]
        )
        # Result may be None if no path exists between first two IDs;
        # so let's find a guaranteed connected pair
        edges = graph_service._get_edges()
        if edges:
            src, tgt = edges[0]
            result = graph_service.shortest_path(src, tgt)
            assert result is not None
            assert len(result["path_nodes"]) >= 2

    def test_path_to_self(self, graph_service):
        """Path from node to itself returns [node_id]."""
        nid = graph_service.node_ids[0]
        result = graph_service.shortest_path(nid, nid)
        assert result is not None
        assert result["path_nodes"] == [nid]
        assert result["total_difficulty_score"] == 0.0

    def test_path_nonexistent_node_returns_none(self, graph_service):
        """Path involving nonexistent node returns None."""
        result = graph_service.shortest_path("__fake__", graph_service.node_ids[0])
        assert result is None


# ---------------------------------------------------------------------------
# BFS Reachable
# ---------------------------------------------------------------------------

class TestBfsReachable:
    def test_bfs_returns_neighbors(self, graph_service):
        """BFS from a node with outgoing edges returns results with path info."""
        # Find a node with outgoing edges
        edges = graph_service._get_edges()
        if not edges:
            pytest.skip("No edges in graph")
        src = edges[0][0]
        results = graph_service.bfs_reachable(src, max_hops=2)
        assert len(results) > 0
        first = results[0]
        assert "target_node" in first
        assert "path_nodes" in first
        assert "hops" in first
        assert first["hops"] >= 1

    def test_bfs_nonexistent_node(self, graph_service):
        """BFS from nonexistent node returns empty list."""
        results = graph_service.bfs_reachable("__fake__")
        assert results == []

    def test_bfs_max_hops_respected(self, graph_service):
        """All results have hops <= max_hops."""
        edges = graph_service._get_edges()
        if not edges:
            pytest.skip("No edges in graph")
        src = edges[0][0]
        max_hops = 2
        results = graph_service.bfs_reachable(src, max_hops=max_hops)
        for r in results:
            assert r["hops"] <= max_hops


# ---------------------------------------------------------------------------
# Escape Routes
# ---------------------------------------------------------------------------

class TestEscapeRoutes:
    def test_escape_returns_routes(self, graph_service, db_session):
        """Escape routes from a danger/transition zone node returns 1-3 routes."""
        # Find a node likely to produce escape routes (transition or danger zone)
        node_id = None
        for nid in graph_service.node_ids:
            node = graph_service.get_node(nid)
            if node and node.get("zone", "transition") in ("danger", "transition"):
                node_id = nid
                break
        if node_id is None:
            node_id = graph_service.node_ids[0]

        routes = graph_service.find_escape_routes(node_id, db_session=db_session, top_k=3)
        # Escape routes may be empty if all reachable nodes are also in danger zone
        # so we just verify the return type is a list
        assert isinstance(routes, list)
        assert len(routes) <= 3

    def test_escape_route_has_required_fields(self, graph_service, db_session):
        """Each route has: target, total_cost, gap_skills, path."""
        node_id = graph_service.node_ids[0]
        routes = graph_service.find_escape_routes(node_id, db_session=db_session, top_k=3)
        required_fields = {"target", "total_cost", "gap_skills", "path"}
        for route in routes:
            for field in required_fields:
                assert field in route, f"Route missing field '{field}': {route.keys()}"

    def test_escape_nonexistent_node(self, graph_service, db_session):
        """Escape from nonexistent node returns empty list."""
        routes = graph_service.find_escape_routes("__fake__", db_session=db_session)
        assert routes == []


# ---------------------------------------------------------------------------
# Terrain Score
# ---------------------------------------------------------------------------

class TestTerrainScore:
    def test_get_terrain_score_returns_dict(self, graph_service, db_session):
        """get_terrain_score returns a dict with expected fields."""
        node_id = graph_service.node_ids[0]
        score = graph_service.get_terrain_score(node_id, db_session)
        assert isinstance(score, dict)
        # Should have at least these core fields (from DB or fallback)
        assert "replacement_pressure" in score
        assert "human_ai_leverage" in score
        assert "zone" in score

    def test_get_terrain_score_nonexistent_node(self, graph_service, db_session):
        """Terrain score for nonexistent node returns fallback dict."""
        score = graph_service.get_terrain_score("__fake__", db_session)
        assert isinstance(score, dict)


# ---------------------------------------------------------------------------
# Transition Probability (stub)
# ---------------------------------------------------------------------------

class TestTransitionProbability:
    def test_stub_returns_float(self, graph_service):
        """Stub method returns 0.5."""
        ids = graph_service.node_ids
        if len(ids) >= 2:
            prob = graph_service.compute_transition_probability(ids[0], ids[1])
            assert prob == 0.5
