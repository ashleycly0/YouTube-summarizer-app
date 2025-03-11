import os
import streamlit as st
import requests
import toml
import json
import html
from llm import answer

# Load API key from credentials.toml or secrets manager
file_path = 'credentials.toml'
if os.path.exists(file_path):
    with open(file_path, 'r') as f:
        secrets = toml.load(f)
else:
    raise FileNotFoundError("Credentials file not found. Please create 'credentials.toml'.")

def fetch_transcript(video_id, language_code=None):
    base_url = "https://yt.vl.comp.polyu.edu.hk/transcript"
    params = {
        "password": "for_demo",
        "video_id": video_id
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        title = data.get('video_title', '')
        transcript = data.get('transcript', '')
        videoid = data.get('video_id', '')
        return {
            "title": title,
            "transcript": transcript,
            "video_id": videoid
        }
    else:
        st.error("Error fetching transcript.")
        return None

def count_tokens(text):
    return len(text.split())

def escape_html(text):
    return html.escape(text)

def download_HTML(title, detail_summary):
    html_content = f"""
    <html>
    <head>
        <title>Detailed Summary of {title}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
            }}
            h1 {{
                color: #333;
            }}
            h2 {{
                color: #555;
            }}
            p {{
                line-height: 1.6;
            }}
            a {{
                color: blue;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <h1>Detailed Summary of {title}</h1>
        {detail_summary}
    </body>
    </html>
    """
    with open("detailed_summary.html", "w") as f:
        f.write(html_content)

def generate_summary_handler():
    video_id = video_url.split("v=")[-1]
    transcript_data = fetch_transcript(video_id, language)

    if transcript_data:
        title = transcript_data['title']
        transcript = transcript_data['transcript']

        limited_transcript = transcript[:100]  # Limit to first 100 characters

        data = {
            "transcript": limited_transcript,
            "language": language
        }

        system_prompt = "You are an assistant that summarizes video transcripts."
        summary_language = st.session_state["language"]
        user_prompt = f"Here is the transcript of '{title}': {data['transcript']}. Please summarize it in {summary_language}."

        total_tokens = count_tokens(system_prompt) + count_tokens(user_prompt)

        if total_tokens > 2000:
            st.warning("Transcript is too long. It will be truncated.")
            truncated_transcript = data['transcript'][:1000]  
            user_prompt = f"Here is a truncated transcript of '{title}': {truncated_transcript}. Please summarize it in {summary_language}."

        model_type = "github" if st.session_state["use_github"] else "openrouter"

        try:
            raw_response = answer(system_prompt, user_prompt, model_type)
            st.subheader("Summary of " + title)
            st.write("YouTube Video: " + "https://www.youtube.com/watch?v=" + video_id)
            st.write(raw_response)

            st.session_state["latest_summary"] = {
                "title": title,
                "summary": raw_response,
                "video_id": video_id
            }

            if download_HTML(title, raw_response):  # Automatically generate HTML after summary generation
                with open("summary.html", "rb") as f:
                    st.download_button("Download Summary as HTML", f, file_name="summary.html", mime="text/html")

        except ValueError as e:
            st.error(f"Error generating summary: {e}")
        except json.JSONDecodeError:
            st.error("Received an invalid JSON response from the API. Check the raw response.")

def generate_youtube_links(video_id, start_time):
    start_seconds = start_time[0:1] * 60 + start_time[2:3]

    start_link = f"https://www.youtube.com/watch?v={video_id}&t={start_seconds}"

    return start_link



def generate_detail_summary_handler():
    video_id = video_url.split("v=")[-1]
    transcript_data = fetch_transcript(video_id, language)

    if transcript_data:
        title = transcript_data['title']
        transcript = transcript_data['transcript']

        # Create a dictionary for limited_transcript
        limited_transcript = {
            "text": transcript[:50]  # Limit to first 100 characters
        }

        data = {
            "transcript": limited_transcript,
            "language": language
        }

        summary_language = st.session_state["language"]

        # Define system_prompt before using it
        system_prompt = (
            f"You are an assistant that separates the sessions of video transcripts {limited_transcript['text']} "
            f"(at least 2 sessions or more), provides timestamps with their starting time YouTube URL, and summarizes "
            f"each session with {summary_language}."
        )

        user_prompt = (
            f"Here is a formatting example and summarize in {summary_language}:\n"
            f"Session ..: ..\n"
            f"Timestamp: ... - ... (in mm:ss)\n"
            f"Timestamp URL: {generate_youtube_links(video_id, (0, 0))} (in mm:ss)\n"
            f"Transcript: {limited_transcript['text']} and showing the text within the corresponding Timestamp\n"
            f"Summary: ..."
        )

        total_tokens = count_tokens(system_prompt) + count_tokens(user_prompt)

        if total_tokens > 2000:
            st.warning("Transcript is too long. It will be truncated.")
            limited_transcript['text'] = transcript[:1000]  # Truncate to first 1000 characters
            system_prompt = (
                f"You are an assistant that separates the sessions of video transcripts {limited_transcript['text']} "
                f"(at least 2 sessions or more), provides timestamps with their starting time YouTube URL, and summarizes "
                f"each session with {summary_language}."
            )
            user_prompt = (
                f"Here is a truncated formatting example and summarize in {summary_language}:\n"
                f"Session ..: ..\n"
                f"Timestamp: ... - ... (in mm:ss)\n"
                f"Timestamp URL: {generate_youtube_links(video_id, (0, 0))} (in mm:ss)\n"
                f"Transcript: {limited_transcript['text']} and showing the text within the corresponding Timestamp\n"
                f"Summary: ..."
            )

        model_type = "github" if st.session_state["use_github"] else "openrouter"

        try:
            raw_response = answer(system_prompt, user_prompt, model_type)
            st.subheader("Summary of " + title)
            st.write("YouTube Video: " + "https://www.youtube.com/watch?v=" + video_id)
            st.write(raw_response)

            st.session_state["latest_summary"] = {
                "title": title,
                "summary": raw_response,
                "video_id": video_id
            }

            if download_HTML(title, raw_response):  # Automatically generate HTML after summary generation
                with open("summary.html", "rb") as f:
                    st.download_button("Download Summary as HTML", f, file_name="summary.html", mime="text/html")

        except ValueError as e:
            st.error(f"Error generating summary: {e}")
        except json.JSONDecodeError:
            st.error("Received an invalid JSON response from the API. Check the raw response.")

# Streamlit UI
with st.sidebar:
    title_streamlit = st.title("YouTube Video Summary Generator")
    video_url = st.text_input("YouTube URL:", "https://www.youtube.com/watch?v=rv4LlmLmVWk", key="video_input")
    st.session_state["video_url"] = video_url
    language = st.selectbox("Select Language:", ["en", "zh-CN", "zh-TW"], key="language_select")
    st.session_state["language"] = language
    st.session_state["use_github"] = st.radio("Select API:", ("GitHub", "Openrouter"), index=0)
    button = st.button("Generate Summary", on_click=generate_summary_handler, key="generate_summary")
    button = st.button("Generate Detail Summary", on_click=generate_detail_summary_handler, key="generate_detail_summary")
