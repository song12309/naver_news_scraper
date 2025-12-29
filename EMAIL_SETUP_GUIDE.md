# 이메일 전송 설정 가이드

## Gmail 앱 비밀번호 생성 방법

Gmail로 이메일을 보내려면 **앱 비밀번호**가 필요합니다. (보안을 위해 일반 비밀번호는 사용할 수 없습니다)

### 1단계: Google 계정 설정

1. [Google 계정](https://myaccount.google.com/) 페이지로 이동
2. 왼쪽 메뉴에서 **보안** 클릭

### 2단계: 2단계 인증 활성화 (필수)

앱 비밀번호를 생성하려면 먼저 2단계 인증을 활성화해야 합니다.

1. 보안 페이지에서 **2단계 인증** 찾기
2. **시작하기** 클릭
3. 안내에 따라 2단계 인증 설정

### 3단계: 앱 비밀번호 생성

1. [앱 비밀번호 페이지](https://myaccount.google.com/apppasswords) 접속
2. **앱 선택** 드롭다운에서 "기타(맞춤 이름)" 선택
3. 이름 입력: "네이버 뉴스 스크래퍼" (또는 원하는 이름)
4. **생성** 클릭
5. 생성된 16자리 비밀번호 복사 (공백 제외)

### 4단계: 스크립트 설정

`naver_news_scraper_v2.py` 파일을 열고 다음 부분을 수정하세요:

```python
# ========== 설정 ==========
# 이메일 설정
GMAIL_USER = "your_email@gmail.com"  # 여기에 본인의 Gmail 주소 입력
GMAIL_PASSWORD = "your_app_password"  # 여기에 생성한 앱 비밀번호 입력
RECIPIENT_EMAIL = "andysong1616@gmail.com"  # 수신자 이메일 (이미 설정됨)
```

예시:
```python
GMAIL_USER = "myemail@gmail.com"
GMAIL_PASSWORD = "abcd efgh ijkl mnop"  # 공백 포함해도 됩니다
RECIPIENT_EMAIL = "andysong1616@gmail.com"
```

## 실행 방법

설정을 완료한 후 스크립트를 실행하세요:

```bash
python naver_news_scraper_v2.py
```

## 예상 결과

1. 네이버 뉴스 수집
2. CSV 및 JSON 파일 생성
3. HTML 형식의 이메일 전송
4. `andysong1616@gmail.com`으로 뉴스 결과 수신

## 이메일 형식

전송되는 이메일은 다음과 같은 정보를 포함합니다:

- 📰 제목: "네이버 뉴스 스크래핑 결과 - [날짜 시간]"
- 📊 요약 정보: 수집 시간, 총 기사 수, 키워드 목록
- 🔍 키워드별 그룹화된 뉴스 기사
- 각 기사: 제목(링크), 언론사, 발행일

## 문제 해결

### "이메일 인증 실패" 오류

- Gmail 계정과 앱 비밀번호가 올바른지 확인
- 앱 비밀번호를 새로 생성해서 다시 시도
- 2단계 인증이 활성화되어 있는지 확인

### "보안 수준이 낮은 앱" 오류

- 앱 비밀번호를 사용하면 이 문제가 발생하지 않습니다
- 일반 비밀번호 대신 반드시 앱 비밀번호를 사용하세요

### 이메일이 도착하지 않음

- 스팸 폴더 확인
- Gmail 발신 한도 확인 (일일 약 500통)
- 콘솔 출력에서 "✓ 이메일 전송 완료" 메시지 확인

## 참고 링크

- [Google 앱 비밀번호 도움말](https://support.google.com/accounts/answer/185833)
- [Gmail SMTP 설정](https://support.google.com/mail/answer/7126229)
