

from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
import operator
from agent_logic import GeminiLLM, ReActAgent
from tools import BrowserTools


class AgentState(TypedDict):

    messages: List[str]
    task: str
    iteration: int
    max_iterations: int
    result: Dict[str, Any]


class BrowserAgentGraph:
    
    def __init__(self, llm: GeminiLLM, tools: BrowserTools, max_iterations: int = 3):
        self.llm = llm
        self.tools = tools
        self.max_iterations = max_iterations
        self.agent = ReActAgent(llm, tools, max_iterations)
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        
        workflow = StateGraph(AgentState)
        
        workflow.add_node("llm_node", self._llm_node)
        workflow.add_node("tools_node", self._tools_node)
        workflow.add_node("output_node", self._output_node)
        
        workflow.set_entry_point("llm_node")
        
        workflow.add_conditional_edges(
            "llm_node",
            self._should_continue,
            {
                "continue": "tools_node",
                "end": "output_node"
            }
        )
        
        # Stop right after a tool step finished the task instead of paying for
        # one more LLM call whose output would be thrown away.
        workflow.add_conditional_edges(
            "tools_node",
            lambda state: "end" if state.get("result") is not None else "continue",
            {"continue": "llm_node", "end": "output_node"},
        )
        
        workflow.add_edge("output_node", END)
        
        return workflow.compile()
    
    def _llm_node(self, state: AgentState) -> AgentState:
        """
        LLM reasoning node
        LLM'den bir sonraki adımı planla
        """
        prompt = self.agent.build_prompt(state["task"])
        
        llm_output = self.llm.generate(prompt)
        
        state["messages"].append(f"AI: {llm_output}")
        state["iteration"] += 1
        
        self.agent.history.append(f"\n--- İTERASYON {state['iteration']} ---")
        self.agent.history.append(f"LLM OUTPUT:\n{llm_output}")
        
        return state
    
    def _tools_node(self, state: AgentState) -> AgentState:

        print("\n[DEBUG] LangGraph _tools_node çağrıldı")
        
        last_message = state["messages"][-1]
        llm_output = last_message.replace("AI: ", "")
        
        print(f"[DEBUG] LLM output parse edilecek: {llm_output[:100]}...")
        
        actions = self.agent.parse_actions(llm_output)
        
        print(f"[DEBUG] Parse edilen action sayısı: {len(actions)}")
        
        if not actions:
            observation = "OBSERVATION: LLM'den geçerli ACTION bulunamadı"
            state["messages"].append(f"TOOL: {observation}")
            self.agent.history.append(observation)
            return state
        
        observations = []
        for action_name, args in actions:
            result = self.agent.execute_action(action_name, args)
            observation = f"OBSERVATION: {result['message']}"
            observations.append(observation)
            self.agent.history.append(observation)
            
            if action_name == "VERIFY_TEXT" and result.get("verified", False):
                state["result"] = self.agent.evaluate_run(
                    success=True, iterations=state["iteration"]
                )
            elif action_name == "DONE" and result.get("done", False):
                self.agent.history.append("\n✅ LLM görevi tamamlandı olarak işaretledi")
                if state.get("result") is None:
                    state["result"] = self.agent.evaluate_run(iterations=state["iteration"])
                break
        
        state["messages"].append(f"TOOL: {chr(10).join(observations)}")
        
        return state
    
    def _output_node(self, state: AgentState) -> AgentState:
        if "result" not in state or state["result"] is None:
            state["result"] = self.agent.evaluate_run(iterations=state["iteration"])
        
        return state
    
    def _should_continue(self, state: AgentState) -> str:
        if state.get("result") is not None:
            return "end"
        
        if state["iteration"] >= state["max_iterations"]:
            return "end"
        
        last_message = state["messages"][-1]
        if "ACTION:" in last_message:
            return "continue"
        
        return "continue"
    
    def run(self, task: str) -> dict:

        initial_state = {
            "messages": [f"HUMAN: {task}"],
            "task": task,
            "iteration": 0,
            "max_iterations": self.max_iterations,
            "result": None
        }
        
        self.agent.history = []
        self.agent.history.append(f"=== GÖREV: {task} ===")
        
        try:
            final_state = self.graph.invoke(initial_state)
            result = final_state.get("result")
            if result is None:
                result = self.agent.evaluate_run()
            return result
        except Exception as e:
            return {
                "status": "FAILED",
                "message": f"Graph execution error: {str(e)}",
                "execution_trace": self.agent.history,
                "iterations": 0
            }


def create_agent_graph(llm: GeminiLLM, tools: BrowserTools, max_iterations: int = 3) -> BrowserAgentGraph:
    return BrowserAgentGraph(llm, tools, max_iterations)
