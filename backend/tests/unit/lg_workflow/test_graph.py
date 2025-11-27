import unittest
from app.core.llm.lg_workflow.graph import create_workflow

class TestGraph(unittest.TestCase):
    def test_create_workflow(self):
        """Test that the workflow graph can be created and compiled."""
        user_id = "test_user"
        try:
            app = create_workflow(user_id)
            self.assertIsNotNone(app)
            # If we can get the graph, it means it compiled successfully
            self.assertIsNotNone(app.get_graph())
        except Exception as e:
            self.fail(f"Failed to create workflow: {e}")

if __name__ == '__main__':
    unittest.main()
