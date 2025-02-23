import streamlit as st
import builtins
import sys
import io
from pathlib import Path

def mock_input(prompt=""):
    if not hasattr(mock_input, "called"):
        mock_input.called = True
        return "exit"
    else:
        raise EOFError

builtins.input = mock_input

from main import create_agent, PERSONALITY_PROMPT

agent = create_agent()  # build the agent here in Streamlit

st.set_page_config(page_title="Mijo Ajentu", page_icon="🤖", layout="centered")

dark_css = """
<style>
#MainMenu, header, footer {
    visibility: hidden;
}

body, [data-testid="stAppViewContainer"] {
    background-color: #000000 !important;
    color: #F0F0F0;
    margin: 0;
    padding: 0;
    font-family: sans-serif;
}
.block-container {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

/* The response box now has a border and wraps text properly */
.response-box {
    background-color: #000000;
    border: 1px solid #444;
    border-radius: 5px;
    padding: 1rem;
    margin-top: 1rem;
    font-size: 1.2rem;
    font-weight: bold;
    color: #FF5C5C;
    font-family: 'Courier New', monospace;
    white-space: pre-wrap;       /* Preserve line breaks, wrap text */
    word-break: break-word;      /* Break long words if needed */
}

h3 {
    color: #FF5C5C;
}
</style>
"""
st.markdown(dark_css, unsafe_allow_html=True)

svg_path = Path("logo/mezo.svg")
if svg_path.exists():
    st.image(str(svg_path), output_format="SVG", width=200)
else:
    st.write("mezo.svg not found in the current directory.")

st.markdown("<h3>Mijo Ajentu</h3>", unsafe_allow_html=True)

# Container at the TOP for the agent's output
response_container = st.container()

# Input form at the BOTTOM
with st.form(key="agent_form"):
    user_input = st.text_input("Enter your command to get rekt on matsnet:")
    submitted = st.form_submit_button("Submit")

# If the user clicked "Submit," run the agent and display output
if submitted:
    if user_input.strip():
        final_prompt = PERSONALITY_PROMPT + "\n\nUser: " + user_input

        # Capture prints from the agent and tools
        captured_output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output

        with st.spinner("Thinking..."):
            try:
                response = agent.invoke(final_prompt)
            except Exception as e:
                sys.stdout = old_stdout
                st.error(f"Error: {e}")
                st.stop()
            finally:
                sys.stdout = old_stdout

        console_output = captured_output.getvalue()

        # Parse final answer
        if isinstance(response, dict):
            final_answer = response.get("output", str(response))
        else:
            final_answer = response

        # Put everything in the top container
        with response_container:
            # Main bot response
            st.markdown(
                f"<div class='response-box'>{final_answer}</div>",
                unsafe_allow_html=True
            )

            # If there's console output, show an expander
            if console_output.strip():
                with st.expander("See more"):
                    st.markdown(
                        f"<pre style='color:#FF5C5C; background-color:#000000; white-space: pre-wrap; word-break: break-word;'>{console_output}</pre>",
                        unsafe_allow_html=True
                    )
    else:
        st.warning("Please enter a command!")