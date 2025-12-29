import feedparser
import datetime
import os
import smtplib
import time
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.parse
import re
import anthropic

# --- 1. Settings ---
KEYWORDS = [
    "K-Content Global Strategy",
    "Korean Startup Exit",
    "Webtoon IP Business",
    "Generative AI Trends Korea",
    "FoodTech Investment"
]
ARCHIVE_FILE = "NEWS_ARCHIVE.md"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# JIT Settings
JIT_MAX_RETRIES = 3
JIT_RETRY_DELAY = 5

# Styles
STYLES = {
    "Insight": """
    - Role: Senior VC Analyst
    - Tone: Professional, analytical
    - Image Style: Minimalist data visualization, isometric tech illustration, corporate blue tones.
    """,
    "Storytelling": """
    - Role: Startup Founder
    - Tone: Emotional, narrative, personal
    - Image Style: Warm photography, cinematic lighting, coffee shop atmosphere, hands on laptop.
    """,
    "Viral": """
    - Role: Gen Z Trend Setter
    - Tone: Hype, punchy, fun
    - Image Style: 3D render, pop art colors, neon lighting, surrealism, high contrast.
    """
}

# --- 2. JIT Engine ---

def jit_retry(func):
    """Retry Decorator"""
    def wrapper(*args, **kwargs):
        for attempt in range(JIT_MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"⚠️ [JIT Warning] Attempt {attempt+1} failed: {e}")
                time.sleep(JIT_RETRY_DELAY + random.uniform(0, 1))
        return None
    return wrapper

def get_latest_news_jit(keyword):
    """Get the LATEST news (Sorted by time)"""
    encoded = urllib.parse.quote(keyword)
    # US English settings for global news
    url = f"https://news.google.com/rss/search?q={encoded}+when:1d&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    
    if not feed.entries: return None
    
    # Sort by published date (Newest first)
    sorted_entries = sorted(feed.entries, key=lambda x: x.published_parsed, reverse=True)
    entry = sorted_entries[0]
    
    return {
        'title': entry.title,
        'link': entry.link,
        'keyword': keyword,
        'pub_date': entry.published
    }

def extract_content(text, tag):
    """Helper to parse Claude output"""
    pattern = f"\[{tag}\](.*?)\[/{tag}\]"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else None

@jit_retry
def generate_content_jit(article):
    """Generate Content using Claude 3 Haiku"""
    if not ANTHROPIC_API_KEY: raise Exception("API Key Missing")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    results = {}

    base_prompt = f"""
    You are an AI content engine. 
    Task: Generate a LinkedIn post (English) and an Image Prompt (English).
    
    [News]: {article['title']} ({article['link']})
    
    [Style Guide]
    {{style_guide}}
    
    [Output Format - Strictly Follow This]
    [POST]
    (Write the post text here. No hashtags at start.)
    [/POST]
    
    [IMAGE]
    (Write the image generation prompt here. Include '--ar 16:9' at the end.)
    [/IMAGE]
    """
    
    for style_name, guide in STYLES.items():
        full_prompt = base_prompt.format(style_guide=guide)
        
        # Use Claude 3 Haiku (Reliable & Fast)
        message = client.messages.create(
            model="claude-3-haiku-20240307", 
            max_tokens=800,
            temperature=0.7,
            messages=[{"role": "user", "content": full_prompt}]
        )
        
        raw = message.content[0].text
        results[style_name] = {
            "text": extract_content(raw, "POST") or "Generation Failed",
            "prompt": extract_content(raw, "IMAGE") or "Prompt Failed"
        }
        time.sleep(1) # Rate limit safety
        
    return results

# --- 3. Email & Main ---

def generate_jit_email(results):
    html = """
    <html>
    <body style="font-family: Helvetica, Arial, sans-serif; color: #333; max-width: 800px; margin: 0 auto;">
        <h2 style="color: #6d28d9; border-bottom: 2px solid #6d28d9; padding-bottom: 10px;">
            ⚡ JIT Content Factory (Claude Engine)
        </h2>
    """
    
    for item in results:
        status_color = "#2da44e" if item['status'] == 'published' else "#cf222e"
        
        html += f"""
        <div style="margin-top: 30px; border: 1px solid #ddd; border-radius: 12px; overflow: hidden;">
            <div style="padding: 15px; background: #f8f9fa; border-bottom: 1px solid #eee; display: flex; justify_content: space-between;">
                <div>
                    <span style="font-size: 11px; font-weight: bold; color: #666; text-transform: uppercase;">{item['keyword']}</span>
                    <h3 style="margin: 5px 0 0 0; font-size:16px;"><a href="{item.get('link','#')}" style="text-decoration: none; color: #111;">{item.get('title', 'News Not Found')}</a></h3>
                </div>
                <div style="font-size:11px; font-weight:bold; color:{status_color}; border:1px solid {status_color}; padding:2px 8px; border-radius:10px; height: fit-content;">
                    {item['status'].upper()}
                </div>
            </div>
        """
        
        if item['status'] == 'published' and item.get('variants'):
            html += """<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; border-top: 1px solid #eee;">"""
            
            styles_map = [
                ("📊 Insight", item['variants'].get('Insight'), "#e8f4fd", "#0366d6"),
                ("☕ Story", item['variants'].get('Storytelling'), "#f0fff4", "#2da44e"),
                ("🔥 Viral", item['variants'].get('Viral'), "#fff8c5", "#d29922")
            ]
            
            for name, data, bg, accent in styles_map:
                if not data: continue
                html += f"""
                <div style="border-right: 1px solid #eee; display: flex; flex-direction: column;">
                    <div style="background:{bg}; padding:8px; font-weight:bold; color:{accent}; font-size:13px;">{name}</div>
                    <div style="padding:15px; font-size:12px; line-height:1.4; flex-grow:1;">{data['text'].replace(chr(10), '<br>')}</div>
                    <div style="background:#2d3748; color:#fff; padding:8px; font-size:10px; margin:10px; border-radius:4px;">
                        <span style="color:#4fd1c5;">🎨 Prompt:</span><br>
                        <span style="font-family:monospace;">{data['prompt'][:100]}...</span>
                    </div>
                </div>
                """
            html += "</div>"
        
        html += "</div>"
        
    html += "</body></html>"
    return html

def send_email(subject, html_body):
    user = os.environ.get("EMAIL_USER")
    pw = os.environ.get("EMAIL_PASSWORD")
    if not user: return
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = user
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(user, pw)
        server.send_message(msg)
        server.quit()
        print("✅ JIT Email Sent")
    except Exception as e:
        print(f"❌ Email Failed: {e}")

def main():
    print("⚡ Starting JIT (Claude)...")
    results = []
    
    for keyword in KEYWORDS[:2]: 
        print(f"🔍 Processing: {keyword}")
        item = {'keyword': keyword, 'status': 'pending'}
        
        # 1. Sourcing (Latest)
        article = get_latest_news_jit(keyword)
        if not article:
            item['status'] = 'jit_failed'
            results.append(item)
            continue
            
        item.update(article)
        
        # 2. Generation (Claude with Retry)
        variants = generate_content_jit(article)
        
        if variants:
            item['variants'] = variants
            item['status'] = 'published'
        else:
            item['status'] = 'jit_failed'
            
        results.append(item)
        
    if results:
        html = generate_jit_email(results)
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        send_email(f"[{today}] ⚡ JIT Brief (English+Prompt)", html)
        
        # Git Auto-save
        try:
            os.system('git config --global user.name "MarketBot"')
            os.system('git config --global user.email "bot@github.com"')
            os.system(f'git add {ARCHIVE_FILE}')
            os.system('git commit -m "Update: JIT Content" || echo "No changes"')
            os.system('git push')
        except: pass

if __name__ == "__main__":
    main()