# Import necessary libraries
from io import StringIO
import openai
import streamlit as st
import traceback
import time
import os
import json
import yfinance as yf
from dotenv import load_dotenv
load_dotenv()

# Set your OpenAI Assistant ID here
assistant_id = os.getenv('ASSISTANT_ID')
# Initialize the OpenAI client (ensure to set your API key in the sidebar within the app)
client = openai

# Define functions
def get_stock_price(ticker):
    """Fetch the latest closing stock price for the given ticker symbol."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        latest_price = hist['Close'][-1]
        return latest_price
    except Exception as e:
        st.error(f'Error fetching stock price for {ticker}: {e}')
        return None

def handle_function_call(run_data):
    try:
        tools_to_call = run_data.required_action.submit_tool_outputs.tool_calls
        tools_output_array = []
        for tool in tools_to_call:
            tool_call_id = tool.id
            function_name = tool.function.name
            function_arg = tool.function.arguments

            output = None
            if function_name == 'get_stock_price':
                arguments_dict = json.loads(function_arg)
                symbol = arguments_dict['symbol']
                st.sidebar.write('Getting stock price for:', symbol)
                output = get_stock_price(symbol)

            if output is not None:
                tools_output_array.append({"tool_call_id": tool_call_id, "output": output})

        return tools_output_array
    except Exception as e:
        st.error(f'Error handling function call: {e}')

def run_openai_thread(prompt):
    if prompt is None:
        return []
    # Initialize session state variables
    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = None
    # Initialize thread
    if st.session_state.thread_id is None:
        thread = client.beta.threads.create(assistant_id=assistant_id)
        st.session_state.thread_id = thread.id
    else:
        thread = client.beta.threads.retrieve(thread_id=st.session_state.thread_id)

    # Run the OpenAI API call
    run_data = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id, prompt=prompt)
    st.session_state.messages.append(prompt)
    while run_data.status not in ['completed', 'failed']:
        time.sleep(1)
        run_data = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run_data.id)
        if run_data.status == 'requires_action':
            tool_outputs = handle_function_call(run_data)
            if tool_outputs:
                client.beta.threads.runs.submit_tool_outputs(thread_id=thread.id, run_id=run_data.id, tool_outputs=tool_outputs)
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    return messages

# Set up the Streamlit page
st.set_page_config(page_title='OpenAI App', page_icon='🤖')
st.title('OpenAI Interactive Assistant')

# Main UI
st.sidebar.title("Settings")
# Check if the user's API key is set
api_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password")
if api_key:
    openai.api_key = api_key
    st.session_state.start_chat = True
elif 'start_chat' in st.session_state and st.session_state.start_chat:
    st.sidebar.error("You must enter your OpenAI API Key to start.")

if 'messages' not in st.session_state:
    st.session_state.messages = []

if st.session_state.start_chat:
    st.sidebar.success("You can start chatting now!")
    user_input = st.text_input("Type your message:", key='user_input')
    if user_input:
        st.spinner(text='In progress...')
        assistant_messages = run_openai_thread(user_input)
        for message in assistant_messages:
            st.write(message.content)
else:
    st.warning("Enter your API key in the sidebar to start.")