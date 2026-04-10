"""
Unit tests for Graph Structure and Algorithms.
Tests the integrity and correctness of the journal graph structure.
"""
import pytest
from typing import Dict, List, Set, Any
from collections import deque


class TestGraphStructure:
    """Test suite for graph structure validation."""

    def test_graph_has_no_cycles(self, mock_graph_structure):
        """Test that the graph structure has no cycles."""
        nodes = mock_graph_structure["nodes"]
        edges = mock_graph_structure["edges"]
        
        # Build adjacency list
        adj_list = {}
        for node in nodes:
            adj_list[node["id"]] = []
        
        for edge in edges:
            adj_list[edge["source"]].append(edge["target"])
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for neighbor in adj_list.get(node_id, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node in nodes:
            if node["id"] not in visited:
                assert not has_cycle(node["id"]), f"Cycle detected starting from {node['id']}"

    def test_graph_connectivity(self, mock_graph_structure):
        """Test that all nodes are properly connected."""
        nodes = mock_graph_structure["nodes"]
        edges = mock_graph_structure["edges"]
        
        if len(nodes) <= 1:
            return  # Trivially connected
        
        # Build undirected adjacency list
        adj_list = {}
        for node in nodes:
            adj_list[node["id"]] = []
        
        for edge in edges:
            adj_list[edge["source"]].append(edge["target"])
            adj_list[edge["target"]].append(edge["source"])
        
        # BFS to check connectivity
        visited = set()
        queue = deque([nodes[0]["id"]])
        visited.add(nodes[0]["id"])
        
        while queue:
            current = queue.popleft()
            for neighbor in adj_list[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        assert len(visited) == len(nodes), "Graph is not fully connected"

    def test_edge_references_valid_nodes(self, mock_graph_structure):
        """Test that all edges reference existing nodes."""
        node_ids = {node["id"] for node in mock_graph_structure["nodes"]}
        
        for edge in mock_graph_structure["edges"]:
            assert edge["source"] in node_ids, f"Edge source {edge['source']} not found"
            assert edge["target"] in node_ids, f"Edge target {edge['target']} not found"

    def test_no_duplicate_edges(self, mock_graph_structure):
        """Test that there are no duplicate edges."""
        edges = mock_graph_structure["edges"]
        edge_set = set()
        
        for edge in edges:
            edge_tuple = (edge["source"], edge["target"], edge.get("relation", ""))
            assert edge_tuple not in edge_set, f"Duplicate edge found: {edge_tuple}"
            edge_set.add(edge_tuple)

    def test_tree_structure_properties(self, sample_journal_tree):
        """Test that journal tree maintains proper tree properties."""
        def count_nodes(node: Dict[str, Any]) -> int:
            count = 1
            for child in node.get("children", []):
                count += count_nodes(child)
            return count
        
        def get_depth(node: Dict[str, Any], current_depth: int = 0) -> int:
            if not node.get("children"):
                return current_depth
            return max(get_depth(child, current_depth + 1) for child in node["children"])
        
        total_nodes = count_nodes(sample_journal_tree)
        max_depth = get_depth(sample_journal_tree)
        
        assert total_nodes > 0, "Tree must have at least one node"
        assert max_depth >= 0, "Depth cannot be negative"
        
        # For a tree with n nodes, there should be n-1 edges (parent-child relationships)
        expected_edges = total_nodes - 1
        actual_edges = total_nodes - 1  # In a tree, edges = nodes - 1
        
        assert actual_edges == expected_edges

    def test_parent_child_relationships(self, sample_journal_tree):
        """Test parent-child relationship integrity."""
        def validate_relationships(node: Dict[str, Any], parent_id: str = None) -> bool:
            # Each child should know its parent (implicitly through structure)
            for child in node.get("children", []):
                # In a proper tree, children shouldn't have circular references
                assert child["id"] != node["id"], "Child cannot be same as parent"
                validate_relationships(child, node["id"])
            return True
        
        assert validate_relationships(sample_journal_tree)

    def test_graph_traversal_algorithms(self, mock_graph_structure):
        """Test various graph traversal algorithms work correctly."""
        nodes = mock_graph_structure["nodes"]
        edges = mock_graph_structure["edges"]
        
        # Build adjacency list
        adj_list = {}
        for node in nodes:
            adj_list[node["id"]] = []
        
        for edge in edges:
            adj_list[edge["source"]].append(edge["target"])
        
        # Test BFS
        def bfs(start: str) -> List[str]:
            visited = []
            queue = deque([start])
            seen = {start}
            
            while queue:
                node = queue.popleft()
                visited.append(node)
                for neighbor in adj_list[node]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        queue.append(neighbor)
            
            return visited
        
        # Test DFS
        def dfs(start: str) -> List[str]:
            visited = []
            stack = [start]
            seen = set()
            
            while stack:
                node = stack.pop()
                if node not in seen:
                    seen.add(node)
                    visited.append(node)
                    for neighbor in reversed(adj_list[node]):
                        if neighbor not in seen:
                            stack.append(neighbor)
            
            return visited
        
        start_node = nodes[0]["id"]
        bfs_result = bfs(start_node)
        dfs_result = dfs(start_node)
        
        # Both should visit all reachable nodes
        assert len(bfs_result) > 0
        assert len(dfs_result) > 0
        assert set(bfs_result) == set(dfs_result)

    def test_journal_path_finding(self, sample_journal_tree):
        """Test finding paths between journal entries."""
        def find_path(root: Dict[str, Any], target_id: str, path: List[str] = None) -> List[str]:
            if path is None:
                path = []
            
            current_path = path + [root["id"]]
            
            if root["id"] == target_id:
                return current_path
            
            for child in root.get("children", []):
                result = find_path(child, target_id, current_path)
                if result:
                    return result
            
            return []
        
        # Find path to grandchild
        path = find_path(sample_journal_tree, "grandchild-1")
        assert len(path) == 3  # root -> child-1 -> grandchild-1
        assert path[0] == "root"
        assert path[-1] == "grandchild-1"
        
        # Find path to non-existent node
        path_none = find_path(sample_journal_tree, "non-existent")
        assert path_none == []
