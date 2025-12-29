import requests
from bs4 import BeautifulSoup
import csv
import json
from datetime import datetime
import time
import urllib.parse
import os

class NaverNewsScraper:
    def __init__(self, history_file='news_history.json'):
        self.base_url = "https://search.naver.com/search.naver"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
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

            # 뉴스 항목 찾기
            news_items = soup.select('div.news_area')

            for item in news_items[:max_results]:
                try:
                    # 제목과 링크
                    title_elem = item.select_one('a.news_tit')
                    if not title_elem:
                        continue

                    title = title_elem.get('title', '')
                    link = title_elem.get('href', '')

                    # 언론사
                    press_elem = item.select_one('a.info.press')
                    press = press_elem.text.strip() if press_elem else ''

                    # 발행일
                    date_elem = item.select_one('span.info')
                    date = date_elem.text.strip() if date_elem else ''

                    article = {
                        'keyword': keyword,
                        'title': title,
                        'link': link,
                        'press': press,
                        'date': date
                    }

                    articles.append(article)

                except Exception as e:
                    print(f"기사 파싱 중 오류 발생: {e}")
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


def main():
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

    print("=" * 50)
    print("네이버 뉴스 스크래퍼 시작")
    print("=" * 50)
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

    # 히스토리 저장
    print("\n" + "=" * 50)
    scraper.save_history()
    print("=" * 50)

    print("\n작업 완료!")


if __name__ == "__main__":
    main()
