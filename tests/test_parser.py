import pytest

from agent_logic import ReActAgent


@pytest.fixture
def agent():
    return ReActAgent(llm=None, tools=None)


def test_simple_action(agent):
    assert agent.parse_actions('ACTION: NAVIGATE("https://example.com")') == [
        ("NAVIGATE", ["https://example.com"])
    ]


def test_selector_with_inner_single_quotes(agent):
    # Regression: the system prompt itself recommends selectors like this one.
    out = agent.parse_actions("""ACTION: FILL("textarea[name='q']", "python")""")
    assert out == [("FILL", ["textarea[name='q']", "python"])]


def test_single_quoted_args_with_inner_double_quotes(agent):
    out = agent.parse_actions("""ACTION: CLICK('a[href="/x"]')""")
    assert out == [("CLICK", ['a[href="/x"]'])]


def test_bare_numeric_argument(agent):
    assert agent.parse_actions("ACTION: WAIT(2000)") == [("WAIT", ["2000"])]


def test_no_args(agent):
    assert agent.parse_actions("ACTION: DONE()") == [("DONE", [])]


def test_parenthesis_inside_quotes(agent):
    out = agent.parse_actions('ACTION: VERIFY_TEXT("#t", "price (USD)")')
    assert out == [("VERIFY_TEXT", ["#t", "price (USD)"])]


def test_case_insensitive_and_thought_text_ignored(agent):
    out = agent.parse_actions('THINK: go.\naction: navigate("http://a")')
    assert out == [("NAVIGATE", ["http://a"])]


def test_no_action(agent):
    assert agent.parse_actions("I am not sure what to do.") == []
