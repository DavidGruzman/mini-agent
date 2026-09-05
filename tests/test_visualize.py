import unittest

from mini_agent.visualize import build_timeline, render_html


class TestBuildTimeline(unittest.TestCase):
    def test_plain_text_exchange(self):
        messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": [{"type": "text", "text": "hello"}]},
        ]
        timeline = build_timeline(messages)
        self.assertEqual(
            timeline,
            [
                {"kind": "text", "role": "user", "text": "hi"},
                {"kind": "text", "role": "assistant", "text": "hello"},
            ],
        )

    def test_tool_call_paired_with_result(self):
        messages = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "let me check"},
                    {"type": "tool_use", "id": "t1", "name": "read_file", "input": {"path": "foo.py"}},
                ],
            },
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "print(1)"}],
            },
        ]
        timeline = build_timeline(messages)
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0], {"kind": "text", "role": "assistant", "text": "let me check"})
        self.assertEqual(
            timeline[1],
            {"kind": "tool_call", "name": "read_file", "input": {"path": "foo.py"}, "output": "print(1)"},
        )

    def test_tool_call_without_result_yet(self):
        messages = [
            {
                "role": "assistant",
                "content": [{"type": "tool_use", "id": "t1", "name": "read_file", "input": {"path": "foo.py"}}],
            }
        ]
        timeline = build_timeline(messages)
        self.assertEqual(len(timeline), 1)
        self.assertIsNone(timeline[0]["output"])

    def test_unmatched_tool_result(self):
        messages = [
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "missing", "content": "orphan"}]}
        ]
        timeline = build_timeline(messages)
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0]["kind"], "tool_call")
        self.assertEqual(timeline[0]["output"], "orphan")

    def test_multiple_parallel_tool_calls(self):
        messages = [
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "a", "name": "read_file", "input": {"path": "a.py"}},
                    {"type": "tool_use", "id": "b", "name": "read_file", "input": {"path": "b.py"}},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "a", "content": "content-a"},
                    {"type": "tool_result", "tool_use_id": "b", "content": "content-b"},
                ],
            },
        ]
        timeline = build_timeline(messages)
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0]["output"], "content-a")
        self.assertEqual(timeline[1]["output"], "content-b")


class TestRenderHtml(unittest.TestCase):
    def test_render_contains_escaped_text_and_collapsible_tool(self):
        timeline = [
            {"kind": "text", "role": "user", "text": "<script>alert(1)</script>"},
            {"kind": "tool_call", "name": "read_file", "input": {"path": "foo.py"}, "output": "some output"},
        ]
        page = render_html("/tmp/project", timeline)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("<details class=\"tool\">", page)
        self.assertIn("read_file", page)
        self.assertIn("some output", page)


if __name__ == "__main__":
    unittest.main()
