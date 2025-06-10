"""
Slack MCP 서버

FastMCP를 사용하여 Slack API와 연동되는 MCP 서버를 구현합니다.
모든 필수 기능과 선택 기능을 포함하며, UTF-8 인코딩과 에러 핸들링을 지원합니다.
"""

import asyncio
import os
import sys
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

# FastMCP 및 Slack API 클라이언트 임포트
from fastmcp import FastMCP
from slack_api import SlackAPIClient, SlackAPIError, SlackMessage, SlackChannel, SlackUser

# MCP 서버 인스턴스 생성
mcp = FastMCP("Slack MCP Server")

# Slack API 클라이언트 초기화
slack_token = os.getenv("SLACK_BOT_TOKEN")
if not slack_token:
    raise ValueError("SLACK_BOT_TOKEN 환경 변수가 설정되지 않았습니다.")

slack_client = SlackAPIClient(slack_token)


def format_timestamp(timestamp: str) -> str:
    """
    Slack 타임스탬프를 읽기 쉬운 형식으로 변환합니다.
    
    Args:
        timestamp: Slack 타임스탬프 (예: "1234567890.123456")
        
    Returns:
        포맷된 날짜 문자열
    """
    try:
        # Slack 타임스탬프는 Unix 타임스탬프 형식
        ts_float = float(timestamp)
        dt = datetime.fromtimestamp(ts_float)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return timestamp


def format_message_list(messages: List[SlackMessage]) -> str:
    """
    메시지 목록을 읽기 쉬운 형식으로 포맷합니다.
    
    Args:
        messages: 메시지 목록
        
    Returns:
        포맷된 메시지 문자열
    """
    if not messages:
        return "메시지가 없습니다."
    
    formatted_messages = []
    for msg in messages:
        timestamp = format_timestamp(msg.timestamp)
        user_display = msg.user_name if msg.user_name else msg.user
        
        formatted_msg = f"[{timestamp}] {user_display}: {msg.text}"
        if msg.thread_ts:
            formatted_msg += " (스레드 답글)"
        
        # 원본 타임스탬프 추가 (이모지 반응 등에 필요)
        formatted_msg += f"\n→ 타임스탬프: {msg.timestamp}"
        
        formatted_messages.append(formatted_msg)
    
    return "\n".join(formatted_messages)


def format_channel_list(channels: List[SlackChannel]) -> str:
    """
    채널 목록을 읽기 쉬운 형식으로 포맷합니다.
    
    Args:
        channels: 채널 목록
        
    Returns:
        포맷된 채널 문자열
    """
    if not channels:
        return "접근 가능한 채널이 없습니다."
    
    formatted_channels = []
    for channel in channels:
        privacy = "비공개" if channel.is_private else "공개"
        membership = "멤버" if channel.is_member else "비멤버"
        
        channel_info = f"#{channel.name} (ID: {channel.id}) - {privacy}, {membership}"
        
        if channel.topic:
            channel_info += f"\n  주제: {channel.topic}"
        if channel.purpose:
            channel_info += f"\n  목적: {channel.purpose}"
        if channel.num_members:
            channel_info += f"\n  멤버 수: {channel.num_members}명"
        
        formatted_channels.append(channel_info)
    
    return "\n\n".join(formatted_channels)


def format_user_list(users: List[SlackUser]) -> str:
    """
    사용자 목록을 읽기 쉬운 형식으로 포맷합니다.
    
    Args:
        users: 사용자 목록
        
    Returns:
        포맷된 사용자 문자열
    """
    if not users:
        return "사용자가 없습니다."
    
    formatted_users = []
    for user in users:
        user_info = f"{user.real_name} (@{user.name}) - ID: {user.id}"
        
        details = []
        if user.email:
            details.append(f"이메일: {user.email}")
        if user.is_bot:
            details.append("봇")
        if user.is_admin:
            details.append("관리자")
        if user.status:
            details.append(f"상태: {user.status}")
        
        if details:
            user_info += f"\n  {', '.join(details)}"
        
        formatted_users.append(user_info)
    
    return "\n\n".join(formatted_users)


# ============================================================================
# 필수 기능 구현
# ============================================================================

@mcp.tool()
async def send_slack_message(channel: str, text: str) -> str:
    """
    지정된 Slack 채널에 메시지를 전송합니다.
    
    Args:
        channel: 채널 ID 또는 채널명 (예: #general, C1234567890)
        text: 전송할 메시지 내용 (UTF-8 한글 지원)
        
    Returns:
        전송 결과 메시지
    """
    try:
        result = slack_client.send_message(channel, text)
        
        # 전송된 메시지 정보 추출
        message_ts = result.get('ts', '')
        channel_id = result.get('channel', '')
        
        return f"✅ 메시지가 성공적으로 전송되었습니다!\n" \
               f"채널: {channel}\n" \
               f"메시지: {text}\n" \
               f"타임스탬프: {format_timestamp(message_ts)}"
        
    except SlackAPIError as e:
        return f"❌ 메시지 전송 실패: {e.error}\n" \
               f"채널: {channel}\n" \
               f"메시지: {text}"
    except Exception as e:
        return f"❌ 예상치 못한 오류 발생: {str(e)}"


@mcp.tool()
async def get_slack_channels() -> str:
    """
    접근 가능한 모든 Slack 채널 목록을 조회합니다.
    
    Returns:
        채널 목록 정보 (ID, 이름, 공개/비공개 여부, 멤버십 상태 포함)
    """
    try:
        channels = slack_client.get_channels()
        
        if not channels:
            return "접근 가능한 채널이 없습니다."
        
        # 채널을 공개/비공개로 분류
        public_channels = [ch for ch in channels if not ch.is_private]
        private_channels = [ch for ch in channels if ch.is_private]
        
        result = f"📋 총 {len(channels)}개의 채널을 찾았습니다.\n\n"
        
        if public_channels:
            result += f"🌐 공개 채널 ({len(public_channels)}개):\n"
            result += format_channel_list(public_channels) + "\n\n"
        
        if private_channels:
            result += f"🔒 비공개 채널 ({len(private_channels)}개):\n"
            result += format_channel_list(private_channels)
        
        return result
        
    except SlackAPIError as e:
        return f"❌ 채널 목록 조회 실패: {e.error}"
    except Exception as e:
        return f"❌ 예상치 못한 오류 발생: {str(e)}"


@mcp.tool()
async def get_slack_channel_history(channel_id: str, limit: int = 10) -> str:
    """
    지정된 채널의 최근 메시지 히스토리를 조회합니다.
    
    Args:
        channel_id: 조회할 채널의 ID
        limit: 조회할 메시지 수 (기본값: 10, 최대: 100)
        
    Returns:
        메시지 히스토리 (메시지 내용, 작성자, 타임스탬프 포함)
    """
    try:
        # limit 값 검증
        limit = max(1, min(limit, 100))
        
        messages = slack_client.get_channel_history(channel_id, limit)
        
        if not messages:
            return f"채널 {channel_id}에 메시지가 없습니다."
        
        # 메시지를 시간순으로 정렬 (오래된 것부터)
        messages.sort(key=lambda x: float(x.timestamp))
        
        result = f"📜 채널 {channel_id}의 최근 {len(messages)}개 메시지:\n\n"
        result += format_message_list(messages)
        
        return result
        
    except SlackAPIError as e:
        return f"❌ 채널 히스토리 조회 실패: {e.error}\n채널 ID: {channel_id}"
    except Exception as e:
        return f"❌ 예상치 못한 오류 발생: {str(e)}"


@mcp.tool()
async def send_slack_direct_message(user_id: str, text: str) -> str:
    """
    특정 사용자에게 1:1 다이렉트 메시지를 전송합니다.
    
    Args:
        user_id: 메시지를 받을 사용자의 ID
        text: 전송할 메시지 내용 (UTF-8 한글 지원)
        
    Returns:
        전송 결과 메시지
    """
    try:
        result = slack_client.send_direct_message(user_id, text)
        
        # 전송된 메시지 정보 추출
        message_ts = result.get('ts', '')
        
        # 사용자 정보 조회
        try:
            user_info = slack_client.get_user_info(user_id)
            user_display = f"{user_info.real_name} (@{user_info.name})"
        except:
            user_display = user_id
        
        return f"✅ 다이렉트 메시지가 성공적으로 전송되었습니다!\n" \
               f"수신자: {user_display}\n" \
               f"메시지: {text}\n" \
               f"타임스탬프: {format_timestamp(message_ts)}"
        
    except SlackAPIError as e:
        return f"❌ 다이렉트 메시지 전송 실패: {e.error}\n" \
               f"사용자 ID: {user_id}\n" \
               f"메시지: {text}"
    except Exception as e:
        return f"❌ 예상치 못한 오류 발생: {str(e)}"


# ============================================================================
# 선택 기능 구현
# ============================================================================

@mcp.tool()
async def get_slack_users(limit: int = 50) -> str:
    """
    워크스페이스의 모든 사용자 목록을 조회합니다.
    
    Args:
        limit: 조회할 사용자 수 (기본값: 50, 최대: 1000)
        
    Returns:
        사용자 목록 정보
    """
    try:
        # limit 값 검증
        limit = max(1, min(limit, 1000))
        
        users = slack_client.get_users(limit)
        
        if not users:
            return "사용자를 찾을 수 없습니다."
        
        # 사용자를 봇과 일반 사용자로 분류
        regular_users = [user for user in users if not user.is_bot]
        bot_users = [user for user in users if user.is_bot]
        
        result = f"👥 총 {len(users)}명의 사용자를 찾았습니다.\n\n"
        
        if regular_users:
            result += f"👤 일반 사용자 ({len(regular_users)}명):\n"
            result += format_user_list(regular_users) + "\n\n"
        
        if bot_users:
            result += f"🤖 봇 사용자 ({len(bot_users)}명):\n"
            result += format_user_list(bot_users)
        
        return result
        
    except SlackAPIError as e:
        return f"❌ 사용자 목록 조회 실패: {e.error}"
    except Exception as e:
        return f"❌ 예상치 못한 오류 발생: {str(e)}"


@mcp.tool()
async def search_slack_messages(query: str, count: int = 20) -> str:
    """
    키워드를 통한 메시지 검색 기능을 제공합니다.
    
    Args:
        query: 검색할 키워드
        count: 반환할 결과 수 (기본값: 20, 최대: 100)
        
    Returns:
        검색 결과
    """
    try:
        # count 값 검증
        count = max(1, min(count, 100))
        
        results = slack_client.search_messages(query, count)
        
        if not results:
            return f"'{query}' 키워드로 검색된 메시지가 없습니다."
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            text = result.get('text', '')
            user = result.get('user', {}).get('name', 'unknown')
            channel = result.get('channel', {}).get('name', 'unknown')
            timestamp = result.get('ts', '')
            
            formatted_result = f"{i}. [{format_timestamp(timestamp)}] #{channel} - @{user}:\n   {text}"
            formatted_results.append(formatted_result)
        
        result_text = f"🔍 '{query}' 검색 결과 ({len(results)}개):\n\n"
        result_text += "\n\n".join(formatted_results)
        
        return result_text
        
    except SlackAPIError as e:
        return f"❌ 메시지 검색 실패: {e.error}\n검색어: {query}"
    except Exception as e:
        return f"❌ 예상치 못한 오류 발생: {str(e)}"


@mcp.tool()
async def upload_slack_file(
    channels: str, 
    file_path: str, 
    title: Optional[str] = None,
    initial_comment: Optional[str] = None
) -> str:
    """
    채널에 파일을 업로드합니다.
    
    Args:
        channels: 업로드할 채널 ID들 (쉼표로 구분) 또는 사용자 ID (DM의 경우)
        file_path: 업로드할 파일 경로
        title: 파일 제목 (선택사항)
        initial_comment: 초기 코멘트 (선택사항)
        
    Returns:
        업로드 결과
    """
    try:
        # 파일 존재 확인
        if not os.path.exists(file_path):
            return f"❌ 파일을 찾을 수 없습니다: {file_path}"
        
        # 사용자 ID인 경우 직접 전달, 그렇지 않으면 리스트로 변환
        if channels.startswith('U') and ',' not in channels:
            # 단일 사용자 ID인 경우
            channel_param = channels
        else:
            # 채널 ID들인 경우 리스트로 변환
            channel_param = [ch.strip() for ch in channels.split(',')]
        
        result = slack_client.upload_file(
            channels=channel_param,
            file_path=file_path,
            title=title,
            initial_comment=initial_comment
        )
        
        file_info = result.get('files', [{}])[0] if result.get('files') else result.get('file', {})
        file_name = file_info.get('name', os.path.basename(file_path))
        file_size = file_info.get('size', 0)
        
        return f"✅ 파일이 성공적으로 업로드되었습니다!\n" \
               f"파일명: {file_name}\n" \
               f"크기: {file_size} bytes\n" \
               f"채널: {channels}\n" \
               f"제목: {title or '없음'}\n" \
               f"코멘트: {initial_comment or '없음'}"
        
    except SlackAPIError as e:
        return f"❌ 파일 업로드 실패: {e.error}\n" \
               f"파일: {file_path}\n" \
               f"채널: {channels}"
    except Exception as e:
        return f"❌ 예상치 못한 오류 발생: {str(e)}"


@mcp.tool()
async def add_slack_reaction(channel: str, timestamp: str, emoji: str) -> str:
    """
    특정 메시지에 이모지 반응을 추가합니다.
    
    Args:
        channel: 채널 ID
        timestamp: 메시지 타임스탬프
        emoji: 이모지 이름 (예: thumbsup, heart, smile)
        
    Returns:
        반응 추가 결과
    """
    try:
        # 이모지 이름에서 콜론 제거
        emoji = emoji.strip(':')
        
        result = slack_client.add_reaction(channel, timestamp, emoji)
        
        return f"✅ 이모지 반응이 성공적으로 추가되었습니다!\n" \
               f"채널: {channel}\n" \
               f"메시지 시간: {format_timestamp(timestamp)}\n" \
               f"이모지: :{emoji}:"
        
    except SlackAPIError as e:
        return f"❌ 이모지 반응 추가 실패: {e.error}\n" \
               f"채널: {channel}\n" \
               f"타임스탬프: {timestamp}\n" \
               f"이모지: {emoji}"
    except Exception as e:
        return f"❌ 예상치 못한 오류 발생: {str(e)}"


@mcp.tool()
async def get_slack_thread_replies(channel: str, thread_ts: str) -> str:
    """
    스레드의 모든 답글을 조회합니다.
    
    Args:
        channel: 채널 ID
        thread_ts: 스레드 타임스탬프
        
    Returns:
        스레드 답글 목록
    """
    try:
        replies = slack_client.get_thread_replies(channel, thread_ts)
        
        if not replies:
            return f"스레드에 답글이 없습니다.\n채널: {channel}\n스레드: {format_timestamp(thread_ts)}"
        
        # 첫 번째 메시지는 원본 메시지이므로 제외
        thread_replies = replies[1:] if len(replies) > 1 else []
        
        result = f"🧵 스레드 답글 ({len(thread_replies)}개):\n"
        result += f"원본 메시지 시간: {format_timestamp(thread_ts)}\n\n"
        
        if thread_replies:
            result += format_message_list(thread_replies)
        else:
            result += "답글이 없습니다."
        
        return result
        
    except SlackAPIError as e:
        return f"❌ 스레드 답글 조회 실패: {e.error}\n" \
               f"채널: {channel}\n" \
               f"스레드: {thread_ts}"
    except Exception as e:
        return f"❌ 예상치 못한 오류 발생: {str(e)}"


@mcp.tool()
async def send_slack_thread_reply(channel: str, thread_ts: str, text: str) -> str:
    """
    스레드에 답글을 전송합니다.
    
    Args:
        channel: 채널 ID
        thread_ts: 스레드 타임스탬프
        text: 답글 내용
        
    Returns:
        답글 전송 결과
    """
    try:
        result = slack_client.send_message(channel, text, thread_ts)
        
        message_ts = result.get('ts', '')
        
        return f"✅ 스레드 답글이 성공적으로 전송되었습니다!\n" \
               f"채널: {channel}\n" \
               f"원본 메시지: {format_timestamp(thread_ts)}\n" \
               f"답글: {text}\n" \
               f"답글 시간: {format_timestamp(message_ts)}"
        
    except SlackAPIError as e:
        return f"❌ 스레드 답글 전송 실패: {e.error}\n" \
               f"채널: {channel}\n" \
               f"스레드: {thread_ts}\n" \
               f"답글: {text}"
    except Exception as e:
        return f"❌ 예상치 못한 오류 발생: {str(e)}"


@mcp.tool()
async def test_slack_connection() -> str:
    """
    Slack API 연결을 테스트합니다.
    
    Returns:
        연결 테스트 결과
    """
    try:
        result = slack_client.test_connection()
        
        team_name = result.get('team', 'Unknown')
        user_name = result.get('user', 'Unknown')
        team_id = result.get('team_id', 'Unknown')
        user_id = result.get('user_id', 'Unknown')
        
        return f"✅ Slack API 연결 성공!\n" \
               f"팀: {team_name} (ID: {team_id})\n" \
               f"봇 사용자: {user_name} (ID: {user_id})\n" \
               f"연결 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
    except SlackAPIError as e:
        return f"❌ Slack API 연결 실패: {e.error}\n" \
               f"토큰을 확인해주세요."
    except Exception as e:
        return f"❌ 예상치 못한 오류 발생: {str(e)}"


# ============================================================================
# 서버 실행
# ============================================================================




def run_server():
    """서버를 실행합니다."""
    try:
        # 연결 테스트
        print("🚀 Slack MCP 서버를 시작합니다...", file=sys.stderr)
        
        # Slack API 연결 테스트
        test_result = slack_client.test_connection()
        print(f"✅ Slack API 연결 성공: {test_result.get('team', 'Unknown')}", file=sys.stderr)
        
        # MCP 서버 실행
        asyncio.run(mcp.run(transport="stdio"))
        
    except Exception as e:
        print(f"❌ 서버 시작 실패: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_server() 