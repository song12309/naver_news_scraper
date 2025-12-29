import requests
from bs4 import BeautifulSoup
import csv
import json
from datetime import datetime
import time
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import getpass
import os

class NaverNewsScraper:
    def __init__(self, history_file='news_history.json'):
        self.base_url = "https://search.naver.com/search.naver"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.history_file = history_file
        self.url_history = self.load_history()

    def search_news(self, keyword, max_results=5):
        """
        네이버 뉴스에서 키워드로 검색하여 최신 뉴스를 가져옵니다.

        Args:
            keyword: 검색할 키워드
            max_results: 가져올 뉴스 개수 (기본값: 5)

        Returns:
            뉴스 기사 리스트
        """
        articles = []

        params = {
            'where': 'news',
            'query': keyword,
            'sort': '1',  # 최신순 정렬
            'start': 1
        }

        try:
            response = requests.get(self.base_url, params=params, headers=self.headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 최신 네이버 뉴스 구조 파싱
            news_items = soup.select('.api_subject_bx')

            count = 0
            for item in news_items:
                if count >= max_results:
                    break

                try:
                    # 제목 찾기 (새로운 구조)
                    title_elem = item.select_one('.sds-comps-text-type-headline1')
                    if not title_elem:
                        continue

                    title = title_elem.get_text().strip()

                    # 링크 찾기
                    link_elem = item.select_one('a[data-heatmap-target=".tit"]')
                    link = link_elem.get('href', '') if link_elem else ''

                    # 언론사 찾기
                    press_elem = item.select_one('.sds-comps-profile-info-title-text')
                    press = ''
                    if press_elem:
                        press_text = press_elem.get_text().strip()
                        # 중첩된 텍스트에서 언론사 이름만 추출
                        press = re.sub(r'\s+', ' ', press_text).strip()

                    # 발행일 찾기
                    date_elem = item.select_one('.sds-comps-profile-info-subtext')
                    date = ''
                    if date_elem:
                        date = date_elem.get_text().strip()

                    if title and link:
                        article = {
                            'keyword': keyword,
                            'title': title,
                            'link': link,
                            'press': press,
                            'date': date
                        }
                        articles.append(article)
                        count += 1

                except Exception as e:
                    continue

            print(f"'{keyword}' 검색 완료: {len(articles)}개 기사 수집")

        except Exception as e:
            print(f"'{keyword}' 검색 중 오류 발생: {e}")

        return articles

    def load_history(self):
        """
        URL 히스토리를 파일에서 불러옵니다.

        Returns:
            set: 이전에 수집한 URL들의 집합
        """
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    urls = set(data.get('urls', []))
                    print(f"히스토리 로드 완료: {len(urls)}개의 URL 기록")
                    return urls
            except Exception as e:
                print(f"히스토리 파일 로드 실패: {e}")
                return set()
        else:
            print("히스토리 파일이 없습니다. 새로 시작합니다.")
            return set()

    def save_history(self):
        """
        현재 URL 히스토리를 파일에 저장합니다.
        """
        try:
            data = {
                'urls': list(self.url_history),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"히스토리 저장 완료: {len(self.url_history)}개의 URL")
        except Exception as e:
            print(f"히스토리 저장 실패: {e}")

    def is_duplicate(self, url):
        """
        URL이 이미 수집된 적이 있는지 확인합니다.

        Args:
            url: 확인할 URL

        Returns:
            bool: 중복이면 True, 아니면 False
        """
        return url in self.url_history

    def add_to_history(self, url):
        """
        URL을 히스토리에 추가합니다.

        Args:
            url: 추가할 URL
        """
        self.url_history.add(url)

    def scrape_multiple_keywords(self, keywords, max_results=5):
        """
        여러 키워드에 대해 뉴스를 검색합니다.
        중복된 URL은 제외합니다.

        Args:
            keywords: 검색할 키워드 리스트
            max_results: 각 키워드당 가져올 뉴스 개수

        Returns:
            모든 뉴스 기사 리스트 (중복 제거된)
        """
        all_articles = []
        duplicate_count = 0

        for keyword in keywords:
            articles = self.search_news(keyword, max_results)

            # 중복 체크 및 필터링
            for article in articles:
                url = article['link']
                if self.is_duplicate(url):
                    duplicate_count += 1
                    print(f"  [중복 제외] {article['title'][:30]}...")
                else:
                    all_articles.append(article)
                    self.add_to_history(url)

            time.sleep(1)  # 서버 부하 방지를 위한 딜레이

        if duplicate_count > 0:
            print(f"\n총 {duplicate_count}개의 중복 기사를 제외했습니다.")

        return all_articles

    def save_to_csv(self, articles, filename='naver_news_results.csv'):
        """
        수집한 뉴스를 CSV 파일로 저장합니다.
        """
        if not articles:
            print("저장할 기사가 없습니다.")
            return

        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['keyword', 'title', 'link', 'press', 'date']
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for article in articles:
                writer.writerow(article)

        print(f"CSV 파일로 저장 완료: {filename}")

    def save_to_json(self, articles, filename='naver_news_results.json'):
        """
        수집한 뉴스를 JSON 파일로 저장합니다.
        """
        if not articles:
            print("저장할 기사가 없습니다.")
            return

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

        print(f"JSON 파일로 저장 완료: {filename}")

    def send_email(self, articles, gmail_user, gmail_password, recipient_email):
        """
        수집한 뉴스를 HTML 형식의 이메일로 전송합니다.

        Args:
            articles: 뉴스 기사 리스트
            gmail_user: Gmail 계정 (발신자)
            gmail_password: Gmail 앱 비밀번호
            recipient_email: 수신자 이메일
        """
        if not articles:
            print("전송할 기사가 없습니다.")
            return False

        # 이메일 제목
        subject = f"네이버 뉴스 스크래핑 결과 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # HTML 이메일 본문 생성
        html_body = self._generate_html_email(articles)

        # 이메일 메시지 생성
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = gmail_user
        msg['To'] = recipient_email

        # HTML 파트 추가
        html_part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(html_part)

        try:
            # Gmail SMTP 서버 연결
            print("이메일 전송 중...")
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(gmail_user, gmail_password)

            # 이메일 전송
            server.send_message(msg)
            server.quit()

            print(f"✓ 이메일 전송 완료: {recipient_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            print("✗ 이메일 인증 실패. Gmail 계정 또는 앱 비밀번호를 확인하세요.")
            print("  앱 비밀번호 생성: https://myaccount.google.com/apppasswords")
            return False
        except Exception as e:
            print(f"✗ 이메일 전송 실패: {e}")
            return False

    def _generate_html_email(self, articles):
        """
        HTML 형식의 이메일 본문을 생성합니다.
        """
        # 키워드별로 기사 그룹화
        grouped = {}
        for article in articles:
            keyword = article['keyword']
            if keyword not in grouped:
                grouped[keyword] = []
            grouped[keyword].append(article)

        # HTML 템플릿
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background-color: #ffffff;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #03C75A;
                    border-bottom: 3px solid #03C75A;
                    padding-bottom: 10px;
                    margin-bottom: 30px;
                }}
                h2 {{
                    color: #1a73e8;
                    margin-top: 30px;
                    margin-bottom: 15px;
                    font-size: 1.3em;
                }}
                .article {{
                    background-color: #f8f9fa;
                    border-left: 4px solid #1a73e8;
                    padding: 15px;
                    margin-bottom: 15px;
                    border-radius: 4px;
                    transition: all 0.3s ease;
                }}
                .article:hover {{
                    background-color: #e8f0fe;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .article-title {{
                    font-size: 1.1em;
                    font-weight: bold;
                    margin-bottom: 8px;
                }}
                .article-title a {{
                    color: #1a73e8;
                    text-decoration: none;
                }}
                .article-title a:hover {{
                    text-decoration: underline;
                }}
                .article-meta {{
                    color: #666;
                    font-size: 0.9em;
                    margin-top: 8px;
                }}
                .press {{
                    display: inline-block;
                    background-color: #e8f0fe;
                    padding: 2px 8px;
                    border-radius: 3px;
                    margin-right: 10px;
                    font-weight: 500;
                }}
                .date {{
                    color: #999;
                }}
                .summary {{
                    background-color: #e8f5e9;
                    padding: 15px;
                    border-radius: 4px;
                    margin-bottom: 30px;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    text-align: center;
                    color: #999;
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📰 네이버 뉴스 스크래핑 결과</h1>

                <div class="summary">
                    <strong>수집 시간:</strong> {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}<br>
                    <strong>총 기사 수:</strong> {len(articles)}개<br>
                    <strong>키워드:</strong> {', '.join(grouped.keys())}
                </div>
        """

        # 키워드별 기사 추가
        for keyword, keyword_articles in grouped.items():
            html += f"""
                <h2>🔍 {keyword} ({len(keyword_articles)}개)</h2>
            """

            for article in keyword_articles:
                html += f"""
                <div class="article">
                    <div class="article-title">
                        <a href="{article['link']}" target="_blank">{article['title']}</a>
                    </div>
                    <div class="article-meta">
                        <span class="press">{article['press']}</span>
                        <span class="date">{article['date']}</span>
                    </div>
                </div>
                """

        html += """
                <div class="footer">
                    네이버 뉴스 스크래퍼 by Python<br>
                    이 이메일은 자동으로 생성되었습니다.
                </div>
            </div>
        </body>
        </html>
        """

        return html


def main():
    print("=" * 50)
    print("네이버 뉴스 스크래퍼 시작")
    print("=" * 50)

    # 이메일 전송 옵션
    print("\n이메일 전송을 하시겠습니까? (y/n): ", end="")
    send_email_option = input().strip().lower()

    GMAIL_USER = None
    GMAIL_PASSWORD = None
    RECIPIENT_EMAIL = None

    if send_email_option == 'y':
        print("\n이메일 전송 설정")
        print("-" * 50)
        GMAIL_USER = input("발신자 Gmail 계정 입력: ").strip()
        GMAIL_PASSWORD = getpass.getpass("Gmail 앱 비밀번호 입력 (입력 내용이 보이지 않습니다): ").strip()
        RECIPIENT_EMAIL = input("수신자 이메일 입력: ").strip()

        if not GMAIL_USER or not GMAIL_PASSWORD or not RECIPIENT_EMAIL:
            print("\n✗ 이메일 정보가 입력되지 않았습니다.")
            print("이메일 전송을 건너뜁니다.")
            send_email_option = 'n'

    # 검색할 키워드 리스트
    keywords = [
        '야놀자',
        '여기어때',
        '아고다',
        '익스피디아',
        '에어비앤비',
        '호텔스닷컴',
        '트립닷컴',
        '스테이폴리오',
        '마이리얼트립'
    ]

    print("\n" + "=" * 50)
    print(f"검색 키워드: {', '.join(keywords)}")
    print(f"각 키워드당 수집 개수: 5개")
    print("=" * 50)

    scraper = NaverNewsScraper()

    # 뉴스 수집
    articles = scraper.scrape_multiple_keywords(keywords, max_results=5)

    print("\n" + "=" * 50)
    print(f"총 {len(articles)}개의 기사를 수집했습니다.")
    print("=" * 50)

    # 결과 출력
    for article in articles:
        print(f"\n[{article['keyword']}] {article['title']}")
        print(f"  언론사: {article['press']}")
        print(f"  발행일: {article['date']}")
        print(f"  링크: {article['link']}")

    # 파일로 저장
    scraper.save_to_csv(articles)
    scraper.save_to_json(articles)

    # 이메일 전송
    if send_email_option == 'y' and GMAIL_USER and GMAIL_PASSWORD and RECIPIENT_EMAIL:
        print("\n" + "=" * 50)
        scraper.send_email(articles, GMAIL_USER, GMAIL_PASSWORD, RECIPIENT_EMAIL)
        print("=" * 50)

    # 히스토리 저장
    print("\n" + "=" * 50)
    scraper.save_history()
    print("=" * 50)

    print("\n작업 완료!")


if __name__ == "__main__":
    main()
