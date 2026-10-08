"""Agent loop and LangGraph wiring, driven by a scripted LLM and fake tools."""
from agent_logic import ReActAgent
from langgraph_graph import BrowserAgentGraph


class ScriptedLLM:
    def __init__(self, outputs):
        self.outputs = list(outputs)

    def generate(self, prompt):
        return self.outputs.pop(0) if self.outputs else "no action"


class FakeTools:
    def __init__(self, verify_ok=True):
        self.calls = []
        self.verify_ok = verify_ok

    def navigate(self, url):
        self.calls.append(("navigate", url))
        return {"success": True, "message": f"went {url}"}

    def screenshot(self, path):
        self.calls.append(("screenshot", path))
        return {"success": True, "message": "shot"}

    def verify_text(self, sel, expected):
        self.calls.append(("verify_text", sel, expected))
        return {
            "success": self.verify_ok,
            "verified": self.verify_ok,
            "message": "VERIFY PASSED" if self.verify_ok else "VERIFY FAILED",
        }

    def wait(self, ms):
        self.calls.append(("wait", ms))
        return {"success": True, "message": "waited"}


PLAN = [
    'ACTION: NAVIGATE("http://x")',
    'ACTION: SCREENSHOT("a.png")',
    'ACTION: VERIFY_TEXT("#s", "ok")',
]


def test_execute_action_routing_and_bad_args():
    tools = FakeTools()
    agent = ReActAgent(ScriptedLLM([]), tools)
    assert agent.execute_action("NAVIGATE", ["http://x"])["success"]
    assert agent.execute_action("WAIT", ["250"])["success"]
    assert tools.calls == [("navigate", "http://x"), ("wait", 250)]
    assert not agent.execute_action("FILL", ["only-selector"])["success"]
    assert "Bilinmeyen" in agent.execute_action("HACK", [])["message"]


def test_simple_loop_passes_and_stops_early():
    agent = ReActAgent(ScriptedLLM(PLAN), FakeTools(), max_iterations=10)
    result = agent.run("task")
    assert result["status"] == "PASSED"
    assert result["iterations"] == 3


def test_simple_loop_fails_when_verification_never_passes():
    agent = ReActAgent(ScriptedLLM(PLAN * 2), FakeTools(verify_ok=False), max_iterations=4)
    result = agent.run("task")
    assert result["status"] == "FAILED"
    assert result["iterations"] == 4


def test_graph_reports_real_iteration_count():
    graph = BrowserAgentGraph(ScriptedLLM(PLAN), FakeTools(), max_iterations=10)
    result = graph.run("task")
    assert result["status"] == "PASSED"
    assert result["iterations"] == 3  # was always max_iterations before the fix


def test_graph_honours_done():
    llm = ScriptedLLM(['ACTION: NAVIGATE("http://x")', "ACTION: DONE()"])
    graph = BrowserAgentGraph(llm, FakeTools(), max_iterations=10)
    result = graph.run("task")
    assert result["iterations"] == 2


def test_graph_stops_at_max_iterations():
    graph = BrowserAgentGraph(ScriptedLLM(["nothing"] * 10), FakeTools(), max_iterations=3)
    result = graph.run("task")
    assert result["status"] == "FAILED"
    assert result["iterations"] == 3


def test_graph_makes_no_llm_call_after_task_finished():
    llm = ScriptedLLM(PLAN + ['ACTION: NAVIGATE("http://never")'])
    BrowserAgentGraph(llm, FakeTools(), max_iterations=10).run("task")
    assert len(llm.outputs) == 1  # the 4th scripted reply was never requested
