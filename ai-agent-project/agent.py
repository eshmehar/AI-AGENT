import os
import sqlite3
import requests
from tavily import TavilyClient
from trafilatura import fetch_url, extract
import PyPDF2
from io import BytesIO
from groq import Groq 

os.environ["GROQ_API_KEY"] = "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"  
os.environ["TAVILY_API_KEY"] =  "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"

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# DATABASE setup
def init_db():
    conn = sqlite3.connect('reports.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reports
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  query TEXT,
                  summary TEXT,
                  sources TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

#  SEARCHES
def search_web(query):# uses tavily api to find 2-3 relevant sources
    try:
        response = tavily.search(query=query, max_results=3)
        return response['results']  # List of title
    except Exception as e:
        print("Search failed:", e)
        return []

# EXTRACT CONTENT in html 
def extract_content(url):# uses trafilatura fro html pages, skips non relevant/empty pages
    try:
        if url.endswith(".pdf"):
            response = requests.get(url)
            pdf_file = BytesIO(response.content)
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text[:5000]  
        else:
            downloaded = fetch_url(url)
            if downloaded is None:
                return ""
            text = extract(downloaded)
            return text[:5000] if text else ""
    except Exception as e:
        print(f"Failed to extract {url}: {e}")
        return ""

# SUMMARIZES WITH LLM 
def summarize_with_llm(query, contents):# sends extracted text to groq to generate a summary
    combined_text = "\n\n---\n\n".join(contents)
    prompt = f"""
    User asked: "{query}"

    Here are some sources found online:

    {combined_text}

    Please write a short, structured summary with key points and mention the sources used.
    Format:
    - Key Point 1
    - Key Point 2
    - ...
    Sources: [list URLs]
    """

    try:
        print("GROQ API KEY:", os.environ.get("GROQ_API_KEY"))
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
           model="llama-3.1-8b-instant",  
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error summarizing: {e}"

#  SAVES
def save_report(query, summary, sources):# inserts all saved information into sqlite database
    conn = sqlite3.connect('reports.db')
    c = conn.cursor()
    c.execute("INSERT INTO reports (query, summary, sources) VALUES (?, ?, ?)",
              (query, summary, str(sources)))
    conn.commit()
    report_id = c.lastrowid
    conn.close()
    return report_id

#  AGENT FUNCTION Runs everything
def run_agent(user_query):
    print(" Searching for:", user_query)
    results = search_web(user_query)

    if not results:
        return "No results found. Try another query."

    contents = []
    source_urls = []

    for result in results[:3]:  # max 3
        url = result['url']
        print(" Fetching:", url)
        content = extract_content(url)
        if content.strip():
            contents.append(content)
            source_urls.append(url)
        else:
            print(" Skipping (empty or failed):", url)

    if not contents:
        return "Could not extract readable content from any sources."

    print(" Summarizing with LLM...")
    summary = summarize_with_llm(user_query, contents)

    print(" Saving to database...")
    report_id = save_report(user_query, summary, source_urls)

    return f" Report #{report_id} saved!\n\n{summary}"

init_db()