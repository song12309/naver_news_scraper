import feedparser
import requests
import json
import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 설정값 ---
KEYWORDS = [
    "한국 F&B 트렌드", "성수동 팝업", "서울 미슐랭 가이드", # F&B
    "국내 유니콘 기업", "스타트업 투자 유치", # 스타트업
    "Private Equity Korea", "MBK 파트너스", "한앤컴퍼니", "IMM PE", "M&A 공시" # PE/Deal
]

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DB_ID = os.environ.get("NOTION_DATABASE_ID")

def get_google_news(keyword):
    """구글 뉴스 RSS 검색"""
    encoded_keyword = keyword.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    
    articles = []
    for entry in feed.entries[:3]: # 키워드당 3개만
        articles.append({
            'title': entry.title,
            'link': entry.link,
            'date': entry.published,
            'keyword': keyword
        })
    return articles

def save_to_notion(article):
    """노션 데이터베이스에 기사 저장"""
    if not NOTION_TOKEN or not NOTION_DB_ID:
        return

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # 노션 DB 컬럼 매칭 (Title, Keyword, Link, Date)
    data = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Title": {"title": [{"text": {"content": article['title']}}]},
            "Keyword": {"select": {"name": article['keyword']}},
            "Link": {"url": article['link']},
            "Date": {"date": {"start": datetime.datetime.now().isoformat().split('T')[0]}}
        }
    }
    
    try:
        requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
    except Exception as e:
        print(f"노션 저장 실패: {e}")

def generate_linkedin_draft(articles):
    draft = "🚀 [Today's Market Insight] F&B, Unicorn & PE Deals\n\n"
    for art in articles:
        draft += f"✅ {art['title']}\n🔗 {art['link']}\n\n"
    draft += "#MarketWatch #Investment #KoreaBusiness"
    return draft

def send_email(subject, body):
    gmail_user = os.environ.get("EMAIL_USER")
    gmail_password = os.environ.get("EMAIL_PASSWORD")
    
    if not gmail_user or not gmail_password:
        return

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = gmail_user
    msg['To'] = gmail_user # 나에게 보내기
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        print("✅ 이메일 발송 완료")
    except Exception as e:
        print(f"❌ 이메일 에러: {e}")

def main():
    print("🔎 마켓 워처 가동 시작...")
    all_articles = []
    
    for keyword in KEYWORDS:
        print(f"수집 중: {keyword}")
        news_items = get_google_news(keyword)
        for item in news_items:
            all_articles.append(item)
            save_to_notion(item) # 노션에 하나씩 저장
            
    print(f"총 {len(all_articles)}개 수집 및 노션 저장 완료.")
    
    if all_articles:
        draft = generate_linkedin_draft(all_articles)
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        send_email(f"[{today}] 마켓 워처 리포트", draft)

if __name__ == "__main__":
    main()
