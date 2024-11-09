from flask import Flask, request, jsonify
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from langgraph.prebuilt import create_react_agent
import os
from dotenv import load_dotenv
from agent import Agent, tools
import json
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()

# Database connection configuration
connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}
first_request_processed = False

# Initialize global variables
pool = None
abot = None


def init_app():
    global pool, abot
    
    # Initialize model
    model = ChatOpenAI(model="gpt-4o-mini", openai_api_key=os.getenv('OPENAI_API_KEY'))
    
    # Initialize connection pool
    pool = ConnectionPool(
        conninfo=os.getenv('AGENT_STATE_DB_URI'),
        max_size=20,
        kwargs=connection_kwargs,
    )
    
    # Initialize agent
    checkpointer = PostgresSaver(pool)
    abot = Agent(model, tools, checkpointer=checkpointer)


@app.before_request
def before_request():
    global first_request_processed
    if not first_request_processed:
        init_app()
        first_request_processed = True

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        print(data)
        thread_id = data.get('thread_id', '1')
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400

        config = {"configurable": {"thread_id": thread_id}}
        res = abot.graph.invoke({"messages": [HumanMessage(content=query)]}, config)
        print(res)
        print(type(res))
        
        # Extract required information
        requirements = None
        candidates = None
        last_ai_message = None
        
        if 'requirements' in res:
            requirements = res['requirements'].requirements
        if 'candidates' in res:
            candidates = res['candidates'].json()
            candidates = json.loads(candidates)
            candidates = candidates['candidates']
            for c in candidates:
                c['raw_content'] = None   
        if 'messages' in res:
            print(res['messages'])
            print(type(res['messages']))
            print(res['messages'][-1])
            last_ai_message = res['messages'][-1].content

        return jsonify({
            'requirements': requirements,
            'candidates': candidates,
            'last_ai_message': last_ai_message
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))



######################################################## TO DO
'''
- Make reply more concise and to the point and interactive
- find products is called before requirements are set, so it doesn't have the context of the requirements
- reply after find products is not concise, it is describing the products think of better ux
- when giving back option it whould be great if they are clickable
- products are not updated in the ui, after second find the products call
- logging errors, trcking the flow of the agent, langsmith, build some test cases
- update requirements and find products are being called simultaeoulsy.
- products expanding ui is annoying
- compare products button is going down
- rank by credibility and popularity too
- handle url rejection
- build an automation to track cadidate provider contribution
- de duplication doesnt seem to work
- some times candidets are suggested directly from chatcpts internal memory
'''