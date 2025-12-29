import feedparser
import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.parse
import anthropic
import re

# --- 1. 설정: 키워드 및 API ---
KEYWORDS = [
    "K-Content Global Strategy",
    "Korean Startup Exit",
    "Webtoon IP Business",
    "Generative AI Trends Korea",
    "FoodTech Investment"
]

ARCHIVE_FILE = "NEWS_ARCHIVE.md"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# --- 2. 스타일 가이드 (프롬프트 엔지니어링) ---
STYLES = {
    "Insight": """
    - 역할: 10년차 벤처 캐피탈 심사역
    - 톤앤매너: 전문적, 분석적, 신뢰감 있는 경어체 (~습니다, ~합니다)
    - 구조: 현상 분석 -> 핵심 데이터 -> 시사점 도출
    - 주의: 이모지 사용 자제, 객관적 사실 위주
    """,
    
    "Storytelling": """
    - 역할: 인사이트를 나누기 좋아하는 스타트업 창업가
    - 톤앤매너: 친근한 구어체, 경험담 공유하듯 자연스럽게 (~하네요, ~같습니다)
    - 구조: "흥미로운 소식이 있어 공유합니다"로 시작 -> 나의 생각 -> 질문 던지기
    - 주의: 적절한 이모지 사용(🔍, 💡), 독자와 대화하듯이 작성
    """,
    
    "Viral": """
    - 역할: 트렌드에 민감한 MZ세대 마케터
    - 톤앤매너: 짧고 간결한 반말, 임팩트 위주 (~다, ~함)
    - 구조: 강렬한 첫 문장(Hook) -> 3줄 요약 -> 결론
    - 주의: 줄글 금지, 불렛포인트 활용, 문장 끝에 🔥 같은 이모지 사용
    """
}

def get_google_news(keyword):
    """구글 뉴스 RSS 검색"""
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}+when:1d&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    if not feed.entries: return None
    
    entry = feed.entries[0]
    return {
        'title': entry.title,
        'link': entry.link,
        'keyword': keyword
    }

def clean_text(text):
    """후처리: 불필요한 기호 제거"""
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def generate_content_variants(article):
    """Claude를 이용해 3가지 스타일로 글 생성"""
    if not ANTHROPIC_API_KEY:
        return {"Error": "API 키가 없습니다."}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    results = {}

    base_prompt = f"""
    아래 뉴스 기사를 바탕으로 링크드인/SNS 포스팅 초안을 작성해줘.
    
    [기사 정보]
    - 키워드: {article['keyword']}
    - 제목: {article['title']}
    - 링크: {article['link']} (글 마지막에 포함할 것)
    
    [스타일 가이드]
    {{style_guide}}
    
    [제약 사항]
    - 글자 수: 공백 포함 400자 내외
    - [1] 같은 참조 번호 넣지 말 것
    """

    for style_name, guide in STYLES.items():
        try:
            full_prompt = base_prompt.format(style_guide=guide)
            
            message = client.messages.create(
                # 여기를 가장 안전한 Haiku 모델로 변경했습니다!
                model="claude-3-haiku-20240307", 
                max_tokens=1000,
                temperature=0.7,
                messages=[{"role": "user", "content": full_prompt}]
            )
            results[style_name] = clean_text(message.content[0].text)
            
        except Exception as e:
            results[style_name] = f"생성 실패: {e}"
            
    return results

def generate_html_email(contents):
    html = """
    <html>
    <body style="font-family: 'Apple SD Gothic Neo', sans-serif; color: #333; max-width: 800px; margin: 0 auto;">
        <h2 style="color: #6d28d9; border-bottom: 2px solid #6d28d9; padding-bottom: 10px;">
            🏭 오늘의 콘텐츠 공장 가동 결과
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
            ("📊 분석가 (Insight)", content['variants'].get('Insight', ''), "#e8f4fd", "#0366d6"),
            ("☕ 창업가 (Story)", content['variants'].get('Storytelling', ''), "#f0fff4", "#2da44e"),
            ("🔥 바이럴 (Viral)", content['variants'].get('Viral', ''), "#fff8c5", "#d29922")
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
        print("✅ 콘텐츠 리포트 발송 완료")
    except Exception as e:
        print(f"❌ 이메일 전송 실패: {e}")

def main():
    print("🏭 콘텐츠 공장 가동 시작...")
    
    contents = []
    
    for keyword in KEYWORDS[:2]: 
        print(f"🔍 검색 및 생성 중: {keyword}")
        article = get_google_news(keyword)
        
        if article:
            variants = generate_content_variants(article)
            article['variants'] = variants
            contents.append(article)
    
    if contents:
        html_body = generate_html_email(contents)
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        send_email(f"[{today}] 콘텐츠 공장 생산 완료 (3가지 버전)", html_body)
        
        # GitHub 자동 저장
        try:
            os.system('git config --global user.name "MarketBot"')
            os.system('git config --global user.email "bot@github.com"')
            os.system(f'git add {ARCHIVE_FILE}')
            os.system('git commit -m "Update: Content Factory Output" || echo "No changes"')
            os.system('git push')
        except:
            pass

if __name__ == "__main__":
    main()