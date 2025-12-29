import feedparser
import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.parse
import anthropic
import re

# --- 1. Settings: Keywords & API ---
KEYWORDS = [
    "K-Content Global Strategy",
    "Korean Startup Exit",
    "Webtoon IP Business",
    "Generative AI Trends Korea",
    "FoodTech Investment"
]

ARCHIVE_FILE = "NEWS_ARCHIVE.md"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# --- 2. Style Guide (English Ver.) ---
STYLES = {
    "Insight": """
    - Role: 10-year Senior VC Analyst
    - Tone: Professional, analytical, trustworthy
    - Structure: Analysis of facts -> Key Data -> Strategic Implication
    - Language: English (US)
    - Note: Use formal business English.
    """,
    
    "Storytelling": """
    - Role: Passionate Startup Founder sharing insights
    - Tone: Casual, engaging, narrative (Story-like)
    - Structure: "Here's something interesting..." -> My thoughts -> Question to audience
    - Language: English (US)
    - Note: Use natural idioms, feel free to use emojis (🔍, 💡).
    """,
    
    "Viral": """
    - Role: Gen Z Trend Marketer on Twitter/Threads
    - Tone: Short, punchy, viral hooks, slang allowed
    - Structure: Strong Hook -> 3 Bullet points -> Conclusion
    - Language: English (US)
    - Note: No long paragraphs. Use emojis (🔥, 🚀).
    """
}

def get_google_news(keyword):
    """Google News RSS (US Settings)"""
    encoded_keyword = urllib.parse.quote(keyword)
    # Changed to US English settings for better global news
    url = f"https://news.google.com/rss/search?q={encoded_keyword}+when:1d&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    if not feed.entries: return None
    
    entry = feed.entries[0]
    return {
        'title': entry.title,
        'link': entry.link,
        'keyword': keyword
    }

def clean_text(text):
    """Post-processing to remove artifacts"""
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def generate_content_variants(article):
    """Generate 3 variants using Claude (English)"""
    if not ANTHROPIC_API_KEY:
        return {"Error": "No API Key"}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    results = {}

    base_prompt = f"""
    Based on the news article below, draft a LinkedIn/Social Media post.
    
    [Article Info]
    - Keyword: {article['keyword']}
    - Title: {article['title']}
    - Link: {article['link']}
    
    [Style Guide]
    {{style_guide}}
    
    [Constraints]
    - Length: Around 150-200 words
    - Output Language: MUST BE ENGLISH ONLY.
    - Do not include citation numbers like [1].
    """

    for style_name, guide in STYLES.items():
        try:
            full_prompt = base_prompt.format(style_guide=guide)
            
            message = client.messages.create(
                model="claude-3-haiku-20240307", # Working Model
                max_tokens=1000,
                temperature=0.7,
                messages=[{"role": "user", "content": full_prompt}]
            )
            results[style_name] = clean_text(message.content[0].text)
            
        except Exception as e:
            results[style_name] = f"Generation Failed: {e}"
            
    return results

def generate_html_email(contents):
    html = """
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #333; max-width: 800px; margin: 0 auto;">
        <h2 style="color: #6d28d9; border-bottom: 2px solid #6d28d9; padding-bottom: 10px;">
            🏭 Global Content Factory (English Edition)
        </h2>
    """
    
    for content in contents:
        html += f"""
        <div style="margin-top: 30px; background: #fff; border: 1px solid #ddd; border-radius: 10px; padding: 20px;">
            <div style="background: #f3f0ff; color: #6d28d9; display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; margin-bottom: 10px;">
                {content['keyword']}
            </div>
            <h3 style="margin: 0 0 15px 0;">
                <a href="{content['link']}" style="text-decoration: none; color: #111;">📰 {content['title']}</a>
            </h3>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
        """
        
        styles = [
            ("📊 VC Analyst", content['variants'].get('Insight', ''), "#e8f4fd", "#0366d6"),
            ("☕ Founder Story", content['variants'].get('Storytelling', ''), "#f0fff4", "#2da44e"),
            ("🔥 Viral/GenZ", content['variants'].get('Viral', ''), "#fff8c5", "#d29922")
        ]
        
        for name, text, bg_color, border_color in styles:
            formatted_text = text.replace('\n', '<br>')
            html += f"""
            <div style="background: {bg_color}; border-top: 3px solid {border_color}; padding: 10px; border-radius: 5px;">
                <h4 style="margin: 0 0 10px 0; color: {border_color}; font-size: 14px;">{name}</h4>
                <div style="font-size: 13px; line-height: 1.5; color: #444;">{formatted_text}</div>
            </div>
            """
            
        html += "</div></div>"
        
    html += "</body></html>"
    return html

def send_email(subject, html_body):
    gmail_user = os.environ.get("EMAIL_USER")
    gmail_password = os.environ.get("EMAIL_PASSWORD")
    if not gmail_user: return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = gmail_user
    msg['To'] = gmail_user
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        print("✅ English Report Sent")
    except Exception as e:
        print(f"❌ Email Failed: {e}")

def main():
    print("🏭 Starting English Content Factory...")
    
    contents = []
    
    for keyword in KEYWORDS[:2]: 
        print(f"🔍 Searching (US): {keyword}")
        article = get_google_news(keyword)
        
        if article:
            variants = generate_content_variants(article)
            article['variants'] = variants
            contents.append(article)
    
    if contents:
        html_body = generate_html_email(contents)
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        send_email(f"[{today}] Global Content Factory (English)", html_body)
        
        # GitHub Auto-save
        try:
            os.system('git config --global user.name "MarketBot"')
            os.system('git config --global user.email "bot@github.com"')
            os.system(f'git add {ARCHIVE_FILE}')
            os.system('git commit -m "Update: English Content" || echo "No changes"')
            os.system('git push')
        except:
            pass

if __name__ == "__main__":
    main()