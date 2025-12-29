#!/bin/bash

# 작업 디렉토리로 이동
cd /Users/andysong1616/Desktop/WVB

# Python 스크립트 실행
/usr/bin/python3 naver_news_scraper_auto.py >> scraper_log.txt 2>&1

# 로그에 구분선 추가
echo "===========================================" >> scraper_log.txt
