"""
Slack API 클라이언트 모듈

이 모듈은 Slack Web API와의 상호작용을 위한 클라이언트 클래스를 제공합니다.
UTF-8 인코딩을 지원하며, 모든 주요 Slack API 기능을 구현합니다.
"""

import json
import os
import requests
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import time


@dataclass
class SlackMessage:
    """Slack 메시지 데이터 클래스"""
    text: str
    user: str
    timestamp: str
    channel: str
    user_name: Optional[str] = None
    thread_ts: Optional[str] = None


@dataclass
class SlackChannel:
    """Slack 채널 데이터 클래스"""
    id: str
    name: str
    is_private: bool
    is_member: bool
    topic: Optional[str] = None
    purpose: Optional[str] = None
    num_members: Optional[int] = None


@dataclass
class SlackUser:
    """Slack 사용자 데이터 클래스"""
    id: str
    name: str
    real_name: str
    email: Optional[str] = None
    is_bot: bool = False
    is_admin: bool = False
    status: Optional[str] = None


class SlackAPIError(Exception):
    """Slack API 에러 클래스"""
    def __init__(self, error: str, response: Optional[Dict] = None):
        self.error = error
        self.response = response
        super().__init__(f"Slack API Error: {error}")


class SlackAPIClient:
    """
    Slack API 클라이언트 클래스
    
    Slack Web API와의 모든 상호작용을 처리합니다.
    UTF-8 인코딩을 지원하며 에러 핸들링을 포함합니다.
    """
    
    BASE_URL = "https://slack.com/api"
    
    def __init__(self, token: str):
        """
        Slack API 클라이언트 초기화
        
        Args:
            token: Slack Bot User OAuth Token
        """
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json; charset=utf-8',
            'User-Agent': 'SlackMCP/1.0'
        }
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Slack API에 HTTP 요청을 보냅니다.
        
        Args:
            method: HTTP 메서드 (GET, POST 등)
            endpoint: API 엔드포인트
            data: 요청 본문 데이터
            params: URL 쿼리 파라미터
            
        Returns:
            API 응답 딕셔너리
            
        Raises:
            SlackAPIError: API 요청 실패 시
        """
        url = f"{self.BASE_URL}/{endpoint}"
        
        print(f"DEBUG: API 요청 - {method} {endpoint}")
        if data:
            print(f"DEBUG: 요청 데이터: {data}")
        if params:
            print(f"DEBUG: 요청 파라미터: {params}")
        
        try:
            if method.upper() == 'GET':
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=params,
                    timeout=30
                )
            else:
                response = requests.post(
                    url, 
                    headers=self.headers, 
                    json=data,
                    timeout=30
                )
            
            print(f"DEBUG: HTTP 응답 상태: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            
            if not result.get('ok', False):
                error_msg = result.get('error', 'Unknown error')
                print(f"DEBUG: Slack API 오류: {error_msg}")
                print(f"DEBUG: 전체 응답: {result}")
                raise SlackAPIError(error_msg, result)
            
            print(f"DEBUG: API 요청 성공")
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: 네트워크 오류: {str(e)}")
            raise SlackAPIError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON 파싱 오류: {str(e)}")
            raise SlackAPIError(f"JSON decode error: {str(e)}")
    
    def send_message(self, channel: str, text: str, thread_ts: Optional[str] = None) -> Dict[str, Any]:
        """
        채널에 메시지를 전송합니다.
        
        Args:
            channel: 채널 ID 또는 채널명 (예: #general, C1234567890)
            text: 전송할 메시지 내용 (UTF-8 지원)
            thread_ts: 스레드 타임스탬프 (스레드 답글인 경우)
            
        Returns:
            전송된 메시지 정보
            
        Raises:
            SlackAPIError: 메시지 전송 실패 시
        """
        # 채널명이 #으로 시작하면 제거
        if channel.startswith('#'):
            channel = channel[1:]
        
        data = {
            'channel': channel,
            'text': text,
            'unfurl_links': True,
            'unfurl_media': True
        }
        
        if thread_ts:
            data['thread_ts'] = thread_ts
        
        return self._make_request('POST', 'chat.postMessage', data)
    
    def get_channels(self, exclude_archived: bool = True) -> List[SlackChannel]:
        """
        접근 가능한 모든 채널 목록을 조회합니다.
        
        Args:
            exclude_archived: 아카이브된 채널 제외 여부
            
        Returns:
            채널 목록
            
        Raises:
            SlackAPIError: 채널 목록 조회 실패 시
        """
        try:
            params = {
                'types': 'public_channel',  # 공개 채널만 조회
                'exclude_archived': exclude_archived,
                'limit': 1000
            }
            
            result = self._make_request('GET', 'conversations.list', params=params)
            channels = []
            
            for channel_data in result.get('channels', []):
                channel = SlackChannel(
                    id=channel_data['id'],
                    name=channel_data['name'],
                    is_private=channel_data.get('is_private', False),
                    is_member=channel_data.get('is_member', False),
                    topic=channel_data.get('topic', {}).get('value'),
                    purpose=channel_data.get('purpose', {}).get('value'),
                    num_members=channel_data.get('num_members')
                )
                channels.append(channel)
            
            return channels
            
        except SlackAPIError as e:
            if 'missing_scope' in str(e.error):
                raise SlackAPIError(
                    "채널 목록 조회 권한이 없습니다. 'channels:read' 스코프가 필요합니다."
                )
            else:
                raise e
    
    def get_channel_history(
        self, 
        channel_id: str, 
        limit: int = 10, 
        oldest: Optional[str] = None,
        latest: Optional[str] = None
    ) -> List[SlackMessage]:
        """
        채널의 메시지 히스토리를 조회합니다.
        
        Args:
            channel_id: 채널 ID
            limit: 조회할 메시지 수 (기본값: 10)
            oldest: 가장 오래된 메시지 타임스탬프
            latest: 가장 최근 메시지 타임스탬프
            
        Returns:
            메시지 목록
            
        Raises:
            SlackAPIError: 히스토리 조회 실패 시
        """
        try:
            params = {
                'channel': channel_id,
                'limit': min(limit, 100)  # 최대 100개로 제한
            }
            
            if oldest:
                params['oldest'] = oldest
            if latest:
                params['latest'] = latest
            
            result = self._make_request('GET', 'conversations.history', params=params)
            messages = []
            
            for msg_data in result.get('messages', []):
                # 봇 메시지나 시스템 메시지 건너뛰기
                if msg_data.get('subtype') in ['bot_message', 'channel_join', 'channel_leave']:
                    continue
                
                message = SlackMessage(
                    text=msg_data.get('text', ''),
                    user=msg_data.get('user', ''),
                    timestamp=msg_data.get('ts', ''),
                    channel=channel_id,
                    thread_ts=msg_data.get('thread_ts')
                )
                messages.append(message)
            
            return messages
            
        except SlackAPIError as e:
            if 'missing_scope' in str(e.error):
                raise SlackAPIError(
                    "채널 히스토리 조회 권한이 없습니다. 'channels:history' 스코프가 필요합니다."
                )
            else:
                raise e
    
    def send_direct_message(self, user_id: str, text: str) -> Dict[str, Any]:
        """
        특정 사용자에게 다이렉트 메시지를 전송합니다.
        
        Args:
            user_id: 메시지를 받을 사용자의 ID
            text: 전송할 메시지 내용
            
        Returns:
            전송된 메시지 정보
            
        Raises:
            SlackAPIError: DM 전송 실패 시
        """
        print(f"DEBUG: DM 전송 시작 - 사용자 ID: {user_id}")
        
        try:
            # 먼저 DM 채널을 열어야 함
            dm_data = {
                'users': user_id
            }
            
            print(f"DEBUG: DM 채널 열기 시도...")
            dm_result = self._make_request('POST', 'conversations.open', dm_data)
            dm_channel_id = dm_result['channel']['id']
            
            print(f"DEBUG: DM 채널 ID 획득: {dm_channel_id}")
            
            # DM 채널에 메시지 전송
            print(f"DEBUG: DM 채널에 메시지 전송 중...")
            result = self.send_message(dm_channel_id, text)
            
            print(f"DEBUG: DM 전송 성공!")
            return result
            
        except SlackAPIError as e:
            print(f"DEBUG: DM 전송 실패 - 오류: {e.error}")
            # 사용자 ID가 잘못되었을 수 있으므로 추가 정보 제공
            if 'user_not_found' in str(e.error):
                print(f"DEBUG: 사용자를 찾을 수 없음. 올바른 사용자 ID인지 확인 필요")
            elif 'channel_not_found' in str(e.error):
                print(f"DEBUG: DM 채널을 열 수 없음. 봇 권한 확인 필요")
            raise e
    
    def get_users(self, limit: int = 1000) -> List[SlackUser]:
        """
        워크스페이스의 모든 사용자 목록을 조회합니다.
        
        Args:
            limit: 조회할 사용자 수 (최대: 1000)
            
        Returns:
            사용자 목록
            
        Raises:
            SlackAPIError: 사용자 목록 조회 실패 시
        """
        params = {
            'limit': min(limit, 1000)
        }
        
        result = self._make_request('GET', 'users.list', params=params)
        users = []
        
        for user_data in result.get('members', []):
            if user_data.get('deleted', False):
                continue
                
            user = SlackUser(
                id=user_data['id'],
                name=user_data['name'],
                real_name=user_data.get('real_name', ''),
                email=user_data.get('profile', {}).get('email'),
                is_bot=user_data.get('is_bot', False),
                is_admin=user_data.get('is_admin', False),
                status=user_data.get('profile', {}).get('status_text')
            )
            users.append(user)
        
        return users
    
    def get_user_info(self, user_id: str) -> SlackUser:
        """
        특정 사용자의 상세 정보를 조회합니다.
        
        Args:
            user_id: 조회할 사용자의 ID
            
        Returns:
            사용자 정보
            
        Raises:
            SlackAPIError: 사용자 정보 조회 실패 시
        """
        params = {
            'user': user_id
        }
        
        result = self._make_request('GET', 'users.info', params=params)
        user_data = result['user']
        
        return SlackUser(
            id=user_data['id'],
            name=user_data['name'],
            real_name=user_data.get('real_name', ''),
            email=user_data.get('profile', {}).get('email'),
            is_bot=user_data.get('is_bot', False),
            is_admin=user_data.get('is_admin', False),
            status=user_data.get('profile', {}).get('status_text')
        )
    
    def search_messages(
        self, 
        query: str, 
        count: int = 20,
        sort: str = 'timestamp'
    ) -> List[Dict[str, Any]]:
        """
        메시지를 검색합니다.
        
        Args:
            query: 검색 쿼리 (예: "hello", "in:#general hello")
            count: 반환할 결과 수 (기본값: 20, 최대: 100)
            sort: 정렬 방식 (timestamp, score)
            
        Returns:
            검색 결과 목록
            
        Raises:
            SlackAPIError: 검색 실패 시
        """
        try:
            params = {
                'query': query,
                'count': min(count, 100),
                'sort': sort
            }
            
            result = self._make_request('GET', 'search.messages', params=params)
            return result.get('messages', {}).get('matches', [])
            
        except SlackAPIError as e:
            if e.error in ['not_allowed_token_type', 'missing_scope']:
                # 검색 권한이 없는 경우 대안 메시지 제공
                raise SlackAPIError(
                    f"메시지 검색 권한이 없습니다. Slack 앱의 OAuth 스코프에 'search:read'를 추가해주세요. "
                    f"현재 오류: {e.error}"
                )
            else:
                raise e
    
    def upload_file(
        self, 
        channels: Union[str, List[str]], 
        file_path: str,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        채널에 파일을 업로드합니다.
        
        Args:
            channels: 채널 ID 또는 채널명
            file_path: 업로드할 파일 경로
            title: 파일 제목 (선택사항)
            initial_comment: 초기 코멘트 (선택사항)
            
        Returns:
            업로드 결과
            
        Raises:
            SlackAPIError: 파일 업로드 실패 시
        """
        if not os.path.exists(file_path):
            raise SlackAPIError(f"파일을 찾을 수 없습니다: {file_path}")
        
        try:
            # 채널명이 주어진 경우 ID로 변환
            if isinstance(channels, str) and not channels.startswith('C'):
                channel_list = self.get_channels()
                channel_id = None
                for channel in channel_list:
                    if channel.name == channels:
                        channel_id = channel.id
                        break
                if not channel_id:
                    raise SlackAPIError(f"채널을 찾을 수 없습니다: {channels}")
                channels = channel_id
            
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            # 1단계: 업로드 URL 요청
            upload_data = {
                'filename': file_name,
                'length': file_size
            }
            
            upload_result = self._make_request('GET', 'files.getUploadURLExternal', params=upload_data)
            upload_url = upload_result['upload_url']
            file_id = upload_result['file_id']
            
            # 2단계: 파일 업로드
            with open(file_path, 'rb') as f:
                files = {'file': (file_name, f, 'application/octet-stream')}
                response = requests.post(upload_url, files=files)
                
                if response.status_code != 200:
                    raise SlackAPIError(f"파일 업로드 실패: HTTP {response.status_code}")
            
            # 3단계: 업로드 완료 처리
            complete_data = {
                'files': [
                    {
                        'id': file_id,
                        'title': title or file_name
                    }
                ],
                'channel_id': channels if isinstance(channels, str) else channels[0]
            }
            
            if initial_comment:
                complete_data['initial_comment'] = initial_comment
            
            return self._make_request('POST', 'files.completeUploadExternal', data=complete_data)
            
        except requests.exceptions.RequestException as e:
            raise SlackAPIError(f"파일 업로드 중 네트워크 오류: {str(e)}")
        except Exception as e:
            raise SlackAPIError(f"파일 업로드 실패: {str(e)}")
    
    def add_reaction(self, channel: str, timestamp: str, name: str) -> Dict[str, Any]:
        """
        메시지에 이모지 반응을 추가합니다.
        
        Args:
            channel: 채널 ID
            timestamp: 메시지 타임스탬프
            name: 이모지 이름 (예: thumbsup, heart)
            
        Returns:
            반응 추가 결과
            
        Raises:
            SlackAPIError: 반응 추가 실패 시
        """
        data = {
            'channel': channel,
            'timestamp': timestamp,
            'name': name
        }
        
        return self._make_request('POST', 'reactions.add', data)
    
    def get_thread_replies(self, channel: str, thread_ts: str) -> List[SlackMessage]:
        """
        스레드의 모든 답글을 조회합니다.
        
        Args:
            channel: 채널 ID
            thread_ts: 스레드 타임스탬프
            
        Returns:
            스레드 답글 목록
            
        Raises:
            SlackAPIError: 스레드 조회 실패 시
        """
        params = {
            'channel': channel,
            'ts': thread_ts
        }
        
        result = self._make_request('GET', 'conversations.replies', params=params)
        messages = []
        
        for msg_data in result.get('messages', []):
            message = SlackMessage(
                text=msg_data.get('text', ''),
                user=msg_data.get('user', 'unknown'),
                timestamp=msg_data.get('ts', ''),
                channel=channel,
                thread_ts=msg_data.get('thread_ts')
            )
            messages.append(message)
        
        return messages
    
    def test_connection(self) -> Dict[str, Any]:
        """
        API 연결을 테스트합니다.
        
        Returns:
            연결 테스트 결과
            
        Raises:
            SlackAPIError: 연결 테스트 실패 시
        """
        return self._make_request('GET', 'auth.test') 