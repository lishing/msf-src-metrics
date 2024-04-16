import os
import openai

endpoint = (
    "https://launchpad-assistant-api.launchpad.tech.gov.sg/services/openai/"
)
api_version = "2023-07-01-preview"
# api_key = os.getenv("OPENAI_API_KEY")
api_key = st.secrets["OPEN_AI_KEY"]

client = openai.AzureOpenAI(
    azure_endpoint=endpoint, api_key=api_key, api_version="2023-03-15-preview"
)

def generate_exec_summary(data_input):
    message_text = [
        {
            "role": "system",
            "content": "You are in charge of the MSF social report application. Provide an executive summary for the report based on the total usage, the metadata such\
            as headers and the content of the report. The report should be in markdown format."
        },
        {
            "role": "user",
            "content": f"[USER SUBMITTED PROBLEM STATEMENT]\n{data_input}",
        },
    ]

    response = client.chat.completions.create(
        model="gpt-35-turbo",
        messages=message_text,
        temperature=0,
        max_tokens=600,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
    )
    
    return response.choices[0].message.content