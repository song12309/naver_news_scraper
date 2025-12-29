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
    """뉴스 내용을 마크다운 파일 최상단에 추가"""
    today = datetime.datetime.now().strftime('%Y년 %m월 %d일')
    
    # 1. 오늘 뉴스 내용 생성
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

    # 2. 기존 파일 읽기 (없으면 생성)
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            old_content = f.read()
    else:
        old_content = "# 📰 Market Watcher 아카이브\n\n"

    # 3. 새 내용 + 옛날 내용 합치기 (최신순 정렬)
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        f.write(old_content.replace("# 📰 Market Watcher 아카이브\n\n", "# 📰 Market Watcher 아카이브\n\n" + new_content))
    
    return new_content # 이메일 본문으로도 사용

def send_email(subject, body):
    gmail_user = os.environ.get("EMAIL_USER")
    gmail_password = os.environ.get("EMAIL_PASSWORD")
    
    if not gmail_user: return

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = gmail_user
    msg['To'] = gmail_user
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
        news_items = get_google_news(keyword)
        all_articles.extend(news_items)
            
    if all_articles:
        # 파일 저장
        markdown_body = update_markdown_archive(all_articles)
        print("✅ 아카이브 파일 업데이트 완료")
        
        # 이메일 전송
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        send_email(f"[{today}] 마켓 워처 리포트", markdown_body)
    else:
        print("수집된 뉴스가 없습니다.")

if __name__ == "__main__":
    main()