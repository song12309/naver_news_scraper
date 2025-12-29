import feedparser
import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.parse

# --- 키워드 설정 ---
KEYWORDS = [
    "성수동 팝업스토어",
    "서울 F&B 트렌드",
    "푸드테크 투자",
    "국내 유니콘 스타트업",
    "스타트업 시리즈 투자",
    "Private Equity Korea",
    "MBK 파트너스",
    "IMM PE",
    "기업 경영권 인수"
]

ARCHIVE_FILE = "NEWS_ARCHIVE.md"

def get_google_news(keyword):
    """구글 뉴스 RSS 검색"""
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}+when:1d&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    
    articles = []
    for entry in feed.entries[:2]:
        articles.append({
            'title': entry.title,
            'link': entry.link,
            'date': entry.published,
            'keyword': keyword
        })
    return articles

def update_markdown_archive(articles):
    """GitHub 저장용: 마크다운 파일 업데이트"""
    today = datetime.datetime.now().strftime('%Y년 %m월 %d일')
    
    new_content = f"## 📅 {today}\n\n"
    
    grouped = {}
    for art in articles:
        k = art['keyword']
        if k not in grouped: grouped[k] = []
        grouped[k].append(art)
        
    for k, items in grouped.items():
        new_content += f"### {k}\n"
        for item in items:
            new_content += f"- [{item['title']}]({item['link']})\n"
        new_content += "\n"
    
    new_content += "---\n\n"

    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            old_content = f.read()
    else:
        old_content = "# 📰 Market Watcher 아카이브\n\n"

    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        f.write(old_content.replace("# 📰 Market Watcher 아카이브\n\n", "# 📰 Market Watcher 아카이브\n\n" + new_content))

def generate_html_email(articles):
    """이메일용: 예쁜 HTML 생성"""
    grouped = {}
    for art in articles:
        k = art['keyword']
        if k not in grouped: grouped[k] = []
        grouped[k].append(art)
    
    # HTML 스타일링 (CSS)
    html = """
    <html>
    <body style="font-family: 'Apple SD Gothic Neo', sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #0366d6; border-bottom: 2px solid #eaecef; padding-bottom: 10px;">
            🚀 Today's Market Watcher
        </h2>
    """
    
    for k, items in grouped.items():
        html += f"<h3 style='margin-top: 20px; color: #24292e; background-color: #f6f8fa; padding: 5px 10px; border-radius: 5px;'>📌 {k}</h3><ul>"
        for item in items:
            # 제목에 링크 걸기 (<a href=...>)
            html += f"<li style='margin-bottom: 8px;'><a href='{item['link']}' style='text-decoration: none; color: #0366d6; font-weight: bold;'>{item['title']}</a></li>"
        html += "</ul>"
        
    html += """
        <div style="margin-top: 30px; font-size: 12px; color: #6a737d; border-top: 1px solid #eaecef; padding-top: 10px;">
            이 메일은 GitHub Actions에 의해 자동 발송되었습니다.
        </div>
    </body>
    </html>
    """
    return html

def send_email(subject, html_body):
    gmail_user = os.environ.get("EMAIL_USER")
    gmail_password = os.environ.get("EMAIL_PASSWORD")
    
    if not gmail_user: return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = gmail_user
    msg['To'] = gmail_user
    
    # HTML 형식으로 첨부 ('html')
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        print("✅ HTML 이메일 발송 완료")
    except Exception as e:
        print(f"❌ 이메일 에러: {e}")

def main():
    print("🔎 마켓 워처 가동 시작...")
    all_articles = []
    
    for keyword in KEYWORDS:
        news_items = get_google_news(keyword)
        all_articles.extend(news_items)
            
    if all_articles:
        # 1. 파일 저장 (마크다운)
        update_markdown_archive(all_articles)
        print("✅ 아카이브 파일 업데이트 완료")
        
        # 2. 이메일 전송 (HTML)
        html_body = generate_html_email(all_articles)
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        send_email(f"[{today}] 마켓 워처 리포트", html_body)
    else:
        print("수집된 뉴스가 없습니다.")

if __name__ == "__main__":
    main()
