# Slack-MCP

FastMCP를 이용한 Slack API 통합 도구입니다. 이 도구를 사용하면 Cursor IDE에서 Slack 워크스페이스와 쉽게 상호작용할 수 있습니다.

## 소개

Slack-MCP는 FastMCP v2를 사용하여 Slack API와 연동되는 MCP(Model Context Protocol) 서버입니다. 이 도구를 통해 LLM(Large Language Model)이 Slack 워크스페이스와 상호작용할 수 있습니다.

## 주요 기능

### 필수 기능

1. **메시지 전송** (`send_slack_message`)
   - 지정된 Slack 채널에 메시지 전송
   - UTF-8 인코딩으로 한글 메시지 지원
   - 매개변수:
     - `channel`: 채널 ID 또는 채널명 (예: #general, C1234567890)
     - `text`: 전송할 메시지 내용

2. **채널 목록 조회** (`get_slack_channels`)
   - 접근 가능한 모든 채널 목록 조회
   - 채널 ID, 이름, 공개/비공개 여부, 멤버십 상태 정보 제공
   - 매개변수: 없음

3. **채널 메시지 히스토리 조회** (`get_slack_channel_history`)
   - 지정된 채널의 최근 메시지 히스토리 조회
   - 메시지 내용, 작성자, 타임스탬프 정보 제공
   - 매개변수:
     - `channel_id`: 조회할 채널의 ID
     - `limit`: 조회할 메시지 수 (기본값: 10, 최대: 100)

4. **다이렉트 메시지 전송** (`send_slack_direct_message`)
   - 특정 사용자에게 1:1 다이렉트 메시지 전송
   - 매개변수:
     - `user_id`: 메시지를 받을 사용자의 ID
     - `text`: 전송할 메시지 내용

### 선택 기능

5. **사용자 목록 조회** (`get_slack_users`)
   - 워크스페이스의 모든 사용자 정보 조회
   - 매개변수:
     - `limit`: 조회할 사용자 수 (기본값: 50)

6. **메시지 검색** (`search_slack_messages`)
   - 키워드를 통한 메시지 검색 기능
   - 매개변수:
     - `query`: 검색할 키워드
     - `count`: 반환할 결과 수 (기본값: 20)

7. **파일 업로드** (`upload_slack_file`)
   - 채널에 파일 업로드 기능
   - 매개변수:
     - `channels`: 업로드할 채널 ID들 (쉼표로 구분) 또는 사용자 ID
     - `file_path`: 업로드할 파일 경로
     - `title`: 파일 제목 (선택사항)
     - `initial_comment`: 초기 코멘트 (선택사항)

8. **메시지 반응 추가** (`add_slack_reaction`)
   - 특정 메시지에 이모지 반응 추가
   - 매개변수:
     - `channel`: 채널 ID
     - `timestamp`: 메시지 타임스탬프
     - `emoji`: 이모지 이름

## 설치 및 설정 가이드

### 1. 필수 패키지 설치

```bash
# 의존성 설치
pip install -r requirements.txt
```

### 2. Slack App 설정

1. [Slack API 페이지](https://api.slack.com/apps)에서 새 앱 생성
2. 다음 Bot Token Scopes 추가:
   - channels:read
   - channels:history
   - channels:write.invites
   - chat:write
   - im:read
   - im:write
   - im:history
   - users:read
   - files:write
   - reactions:write
3. 앱을 워크스페이스에 설치하고 Bot User OAuth Token 복사

### 3. 환경 변수 설정

1. `.env.example` 파일을 `.env`로 복사
2. Slack Bot User OAuth Token 설정
```bash
cp env_example.txt .env
# .env 파일 수정
SLACK_BOT_TOKEN=xoxb-your-token-here
```

### 4. Cursor IDE에 MCP 설정

1. Cursor IDE 열기
2. 설정(Settings) → MCP 탭 열기
3. '새 MCP 추가(Add New MCP)' 클릭
4. 다음 정보 입력:
   - 이름: Slack MCP
   - 명령어: 서버 스크립트의 절대 경로 입력
     ```
     /절대/경로/python /절대/경로/slack_mcp_server.py
     ```
     (Windows의 경우: `C:\절대\경로\python.exe C:\절대\경로\slack_mcp_server.py`)

### 5. MCP 서버 실행

Cursor IDE에서 명령 팔레트(Cmd/Ctrl + Shift + P)를 열고 "MCP: Connect to MCP"를 선택한 후 "Slack MCP"를 선택합니다.

## 주의사항

1. **토큰 보안**
   - `.env` 파일을 `.gitignore`에 추가
   - 토큰을 코드에 직접 작성하지 않기

2. **권한 확인**
   - 필요한 모든 OAuth Scopes 확인
   - 앱이 채널에 초대되어 있는지 확인

3. **에러 처리**
   - API 응답의 에러 메시지 확인
   - 적절한 예외 처리 구현

## 문제 해결

### 자주 발생하는 문제

1. **"missing_scope" 에러**
   - Slack App의 OAuth & Permissions에서 필요한 스코프가 모두 추가되었는지 확인

2. **한글 메시지가 깨지는 경우**
   - HTTP 헤더에 `charset=utf-8`이 포함되어 있는지 확인
   - 메시지 텍스트의 인코딩이 UTF-8인지 확인

3. **채널을 찾을 수 없음**
   - 채널 ID가 올바른지 확인
   - 봇이 채널에 초대되어 있는지 확인

4. **MCP 서버가 연결되지 않음**
   - 절대 경로가 올바르게 설정되었는지 확인
   - 서버가 정상적으로 실행되는지 확인

### 디버깅 팁

- API 응답을 출력하여 구조 확인
- 환경 변수가 올바르게 로드되는지 확인
- 네트워크 연결 상태 확인
- Slack API 문서의 예제 응답과 비교 