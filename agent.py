from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
import operator
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from tool_funcs import CandidateList, get_candidates
import os
from tavily import TavilyClient


load_dotenv()

tavily = TavilyClient(api_key=os.getenv('TAVILY_API_KEY'))

@tool("expert")
def expert(query: str):
    """Finds general knowledge information using Google search. Can also be used
    to augment more 'general' knowledge to a previous specialist query."""
    content = []
    response = tavily.search(query=query, max_results=2)
    for r in response['results']:
        content.append(r['content'])
    return "\n".join(content)

# @tool("update_requirements")
# def update_requirements():
#     """Makes a list of requirements for the product user is looking for, based on your conversation history with the user."""
#     return "updated"

@tool("find_products")
def find_products():
    """Makes a list of requirements for the product user is looking for, based on your conversation history with the user.
    Then, Finds the potential products from the world web/internet using Google search. that meets the user requirements"""
    return "found"

tools = {
    "expert": expert,
    # "update_requirements": update_requirements,
    "find_products": find_products
}


class Requirements(BaseModel):
    requirements: List[str] = Field(description="A list of requirements user is looking for in the product he is searching for")
    query: str = Field(description="A simple short query that summarizes the all user requirements in a sentence. This query will be used to google and find the products user is lookin for. So, write it like a google search  query")
    keywords: List[str] = Field(description="A short list of three keywords that are used to categorize the type of products user is looking for. again these words are used for searching the product.")

class AgentState(TypedDict):
    requirements: Requirements
    candidates: CandidateList
    messages: Annotated[list[AnyMessage], operator.add]

class Agent:
    def __init__(self, model, tools, checkpointer):

        self.orchestrator_system_prompt = """
        You are a software and AI products consultant, you have to search, find and suggest the most appropriate product for the user based on their requirements.
        This is your standard operating procedure you have to follow the steps mentioned below in loop again and again:
        1. First, always try to understand what user is looking for and get a list of his requirements. 
        2. Soon, Use the "find_products" tool to get a list of tools from the internet that meets the collected requirements. 
        Then group these products and give them a highlevel picture of what sought of groups are available according to his requirement and based on the diversity of capabilites of these products ask for more requirements from the user. to help us drilldown on to the exact requirements and to filter out these products.
        Retrived cadidates are shown to the user on the UI. So its redudent to talk about the products in detail.
        3. And repeat.

       Along the way, at anypoint if you are not sure and looking from some knowledge/context (but not looking/suggesting/finding products) or some specific information you can use the "expert" tool by asking it a query to get the most factual, updated knowledge from the internet.
       Always use "find_products" tool only if you are suggesting a list of products/tools to the user. Never answer directly with a list of products/tools.

        Keep it conversational and friendly. Do the above steps in multiple turns until the user gives up.
        """
        self.update_req_system_prompt = "Extract the list of requirements user is looking for in the product from the whole following conversation: "

        graph = StateGraph(AgentState)

        graph.add_node("orchestrator", self.orchestrator)
        graph.add_node("expert", self.expert)
        graph.add_node("update_requirements", self.update_requirements)
        graph.add_node("find_products", self.find_products)

        # graph.add_conditional_edges("orchestrator", self.to_update_requirements, {True: "update_requirements", False: END})
        graph.add_conditional_edges("orchestrator", self.to_expert, {True: "expert", False: END})
        graph.add_conditional_edges("orchestrator", self.to_find_products, {True: "update_requirements", False: END})

        graph.add_edge("expert", "orchestrator")
        graph.add_edge("update_requirements", "find_products")
        graph.add_edge("find_products", "orchestrator")

        graph.set_entry_point("orchestrator")

        self.graph = graph.compile(checkpointer=checkpointer)
        self.model = model
        self.tools = tools

    def orchestrator(self, state: AgentState):
        messages = state['messages']
        if 'requirements' not in state:
            state['requirements'] = Requirements(requirements=[], query='', keywords=[])
        if 'candidates' not in state:
            state['candidates'] = CandidateList(candidates=[])
        print(state)
        if self.orchestrator_system_prompt:
            messages = [SystemMessage(content=self.orchestrator_system_prompt)] + messages +  [SystemMessage(content= "updated user requirements are:" + str(state['requirements'].requirements)), SystemMessage(content= "a list of products that potentially meet user requirements are:" + str(state['candidates'].json()))]
        model = self.model.bind_tools(tools.values())
        message = model.invoke(messages)
        return {'messages': [message]}

    def expert(self, state: AgentState):
        print("Expert called!")
        tool_calls = state['messages'][-1].tool_calls
        results = []
        for t in tool_calls:
            if t['name'] == 'expert':
                print(f"Calling: {t}")
                result = self.tools[t['name']].invoke(t['args'])
                results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))
        print("Back to the model!")
        return {'messages': results}

    def update_requirements(self, state: AgentState):
        print("Update requirements called!")
        # tool_calls = state['messages'][-1].tool_calls
        # results = []
        # for t in tool_calls:
        #     if t['name'] == 'update_requirements':
        #         results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content= "updated list of requirements" )) #+ str("\n".join(requirements.requirements))

        messages = state['messages']
        if self.update_req_system_prompt:
            messages = [SystemMessage(content=self.update_req_system_prompt)] + messages[:-1]
        requirements = self.model.with_structured_output(Requirements).invoke(messages)
        print("Back to the model!")
        return {'requirements': requirements}

    def find_products(self, state: AgentState):
        print("Find products called!")
        tool_calls = state['messages'][-1].tool_calls
        results = []
        for t in tool_calls:
            if t['name'] == 'find_products':
                results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content= "updated list of products" )) #+ str("\n".join(requirements.requirements))

        query = state['requirements'].query + " ".join(state['requirements'].keywords)
        products = get_candidates(query)
        # products = CandidateList(candidates=[])
        print("Back to the model!")
        return {'candidates': products,
                'messages': results}


    def to_expert(self, state: AgentState):
        return self.take_calls(state, 'expert')

    def to_find_products(self, state: AgentState):
        return self.take_calls(state, 'find_products')

    # def to_update_requirements(self, state: AgentState):
    #     return self.take_calls(state, 'update_requirements')

    def take_calls(self, state: AgentState, tool_name):
        tool_calls = state['messages'][-1].tool_calls
        for t in tool_calls:
            if t['name'] == tool_name:
                return True
        return False