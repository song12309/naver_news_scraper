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
import google.generativeai as genai
from openai import OpenAI

# --- 1. JIT 설정 & API 키 ---
KEYWORDS = [
    "K-Content Global Strategy",
    "Korean Startup Exit",
    "Webtoon IP Business",
    "Generative AI Trends Korea",
    "FoodTech Investment"
]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
IMAGE_GEN_API_KEY = os.environ.get("OPENAI_API_KEY")

# JIT(Just-In-Time) 설정
JIT_MAX_RETRIES = 3      # 최대 재시도 횟수
JIT_RETRY_DELAY = 5      # 재시도 대기 시간 (초)
JIT_TOKEN_LIMIT = 800    # 비용 최적화를 위한 토큰 제한

# 스타일 가이드 (영어 버전)
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

# --- 2. JIT 핵심 엔진 (재시도 & 상태관리) ---

def jit_retry(func):
    """실패 시 재시도하는 데코레이터 (JIT Resilience)"""
    def wrapper(*args, **kwargs):
        for attempt in range(JIT_MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"⚠️ [JIT Warning] 시도 {attempt+1}/{JIT_MAX_RETRIES} 실패: {e}")
                time.sleep(JIT_RETRY_DELAY + random.uniform(0, 1)) # 백오프(Backoff) 대기
        print(f"❌ [JIT Failed] 모든 재시도 실패")
        return None
    return wrapper

def get_latest_news(keyword):
    """JIT Freshness: 최신 뉴스 우선 정렬"""
    encoded = urllib.parse.quote(keyword)
    # when:1d (24시간 내) + 정렬 로직 추가
    url = f"https://news.google.com/rss/search?q={encoded}+when:1d&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    
    if not feed.entries: return None
    
    # 최신순 정렬 (published_parsed 기준)
    sorted_entries = sorted(feed.entries, key=lambda x: x.published_parsed, reverse=True)
    entry = sorted_entries[0] # 가장 최신 뉴스 선택
    
    return {
        'title': entry.title,
        'link': entry.link,
        'keyword': keyword,
        'pub_date': entry.published
    }

@jit_retry
def generate_content_jit(article):
    """JIT Content Generation with Gemini"""
    if not GEMINI_API_KEY: raise Exception("API Key Missing")
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # 프롬프트 구성
    base_prompt = f"""
    Generate content for a 'Just-In-Time' news brief.
    
    [News]: {article['title']} ({article['link']})
    
    Tasks:
    1. Create 3 style variations of LinkedIn posts (Insight, Storytelling, Viral).
    2. Create 3 matching Image Prompts.
    
    Output Format (Strict JSON-like structure):
    ---INSIGHT_TEXT---
    (Content)
    ---INSIGHT_PROMPT---
    (Prompt)
    ---STORY_TEXT---
    (Content)
    ---STORY_PROMPT---
    (Prompt)
    ---VIRAL_TEXT---
    (Content)
    ---VIRAL_PROMPT---
    (Prompt)
    """
    
    # 비용 최적화: max_output_tokens 제한
    response = model.generate_content(
        base_prompt,
        generation_config=genai.types.GenerationConfig(max_output_tokens=JIT_TOKEN_LIMIT)
    )
    return response.text

@jit_retry
def generate_image_jit(prompt):
    """JIT Image Generation"""
    if not IMAGE_GEN_API_KEY: return None
    client = OpenAI(api_key=IMAGE_GEN_API_KEY)
    response = client.images.generate(
        model="dall-e-3",
        prompt=f"High quality, {prompt}",
        size="1024x1024",
        quality="standard",
        n=1
    )
    return response.data[0].url

# --- 3. 파싱 및 이메일 전송 ---

def parse_jit_result(text):
    """Gemini 결과물 파싱"""
    if not text: return None
    try:
        data = {}
        for style in ["INSIGHT", "STORY", "VIRAL"]:
            t_tag = f"---{style}_TEXT---"
            p_tag = f"---{style}_PROMPT---"
            
            # 텍스트 추출 (다음 태그 전까지)
            parts = text.split(t_tag)[1].split(p_tag)
            content_text = parts[0].strip()
            
            # 프롬프트 추출 (다음 섹션 전까지, 마지막은 끝까지)
            next_style = "---" if style != "VIRAL" else "★EOF★" # EOF 마커 대용
            prompt_text = parts[1].split("---")[0].strip()
            
            data[style] = {"text": content_text, "prompt": prompt_text}
        return data
    except Exception as e:
        print(f"Parsing Error: {e}")
        return None

def generate_jit_email(results):
    html = """
    <html>
    <body style="font-family: Helvetica, Arial, sans-serif; color: #333; max-width: 800px; margin: 0 auto;">
        <h2 style="color: #6d28d9; border-bottom: 2px solid #6d28d9; padding-bottom: 10px;">
            ⚡ JIT(Just-In-Time) Web Brief
        </h2>
        <p style="font-size:12px; color:#666;">Generated at: """ + datetime.datetime.now().strftime('%H:%M:%S') + """</p>
    """
    
    for item in results:
        status_color = "#2da44e" if item['status'] == 'published' else "#cf222e"
        
        html += f"""
        <div style="margin-top: 30px; border: 1px solid #ddd; border-radius: 12px; overflow: hidden;">
            <div style="padding: 15px; background: #f8f9fa; border-bottom: 1px solid #eee; display: flex; justify_content: space-between;">
                <div>
                    <span style="font-size: 11px; font-weight: bold; color: #666; text-transform: uppercase;">{item['keyword']}</span>
                    <h3 style="margin: 5px 0 0 0; font-size:16px;"><a href="{item.get('link','#')}" style="text-decoration: none; color: #111;">{item.get('title', 'News Fetch Failed')}</a></h3>
                </div>
                <div style="font-size:11px; font-weight:bold; color:{status_color}; border:1px solid {status_color}; padding:2px 8px; border-radius:10px; height: fit-content;">
                    {item['status'].upper()}
                </div>
            </div>
        """
        
        if item['status'] == 'published' and item.get('content'):
            # 3가지 스타일 렌더링
            html += """<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; border-top: 1px solid #eee;">"""
            
            variants = item['content']
            styles_map = [
                ("📊 Insight", variants.get('INSIGHT'), "#e8f4fd", "#0366d6"),
                ("☕ Story", variants.get('STORY'), "#f0fff4", "#2da44e"),
                ("🔥 Viral", variants.get('VIRAL'), "#fff8c5", "#d29922")
            ]
            
            for name, data, bg, accent in styles_map:
                if not data: continue
                html += f"""
                <div style="border-right: 1px solid #eee; display: flex; flex-direction: column;">
                    <div style="background:{bg}; padding:8px; font-weight:bold; color:{accent}; font-size:13px;">{name}</div>
                    <div style="padding:15px; font-size:12px; line-height:1.4; flex-grow:1;">{data['text'].replace(chr(10), '<br>')}</div>
                    <div style="background:#2d3748; color:#fff; padding:8px; font-size:10px; margin:10px;">
                        <span style="color:#4fd1c5;">🎨 Prompt:</span> {data['prompt'][:50]}...
                    </div>
                </div>
                """
            html += "</div>"
            
            # 생성된 이미지 (첫 번째 스타일용 예시)
            if item.get('image_url'):
                 html += f"""<div style="padding:10px; text-align:center; background:#000;"><img src="{item['image_url']}" style="max-width:100%; height:auto; border-radius:8px;"></div>"""
        
        elif item['status'] == 'jit_failed':
             html += """<div style="padding:20px; color:#cf222e; text-align:center;">❌ Content Generation Failed (Max Retries Exceeded)</div>"""
             
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

# --- 메인 실행 ---
def main():
    print("⚡ Starting JIT Market Watcher...")
    results = []
    
    for keyword in KEYWORDS[:2]: # 테스트용 2개
        print(f"🔍 JIT Processing: {keyword}")
        item_result = {'keyword': keyword, 'status': 'pending'}
        
        # 1. 최신 뉴스 소싱 (Sourcing)
        article = get_latest_news(keyword)
        if not article:
            print(f"   -> News Not Found")
            item_result['status'] = 'jit_failed'
            item_result['title'] = 'No Recent News Found'
            results.append(item_result)
            continue
            
        item_result.update(article)
        item_result['status'] = 'jit_pending' # 생성 대기 상태
        
        # 2. 콘텐츠 생성 (Generation with Retry)
        print(f"   -> Generating Content...")
        raw_text = generate_content_jit(article)
        
        if raw_text:
            parsed_content = parse_jit_result(raw_text)
            if parsed_content:
                item_result['content'] = parsed_content
                item_result['status'] = 'published' # 생성 완료 = 발행 준비 완료
                
                # 3. 이미지 생성 (옵션) - Insight 프롬프트 사용
                print(f"   -> Generating Image...")
                img_url = generate_image_jit(parsed_content['INSIGHT']['prompt'])
                if img_url: item_result['image_url'] = img_url
            else:
                item_result['status'] = 'jit_failed'
        else:
            item_result['status'] = 'jit_failed'
            
        results.append(item_result)
        time.sleep(2) # API 속도 조절
        
    # 이메일 발송
    if results:
        html = generate_jit_email(results)
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        send_email(f"[{today}] ⚡ JIT Web Brief Status", html)
        
        # 깃허브 저장
        try:
            os.system('git config --global user.name "MarketBot"')
            os.system('git config --global user.email "bot@github.com"')
            os.system('git add NEWS_ARCHIVE.md')
            os.system('git commit -m "Update: JIT Content" || echo "No changes"')
            os.system('git push')
        except: pass

if __name__ == "__main__":
    main()