#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Root Agent cho MM A2A Ecommerce Chatbot sử dụng Google Gemini
"""

import asyncio
import logging
from google.adk.agents import Agent
from mm_a2a import prompt
from mm_a2a.sub_agents.cng.agent import cng_agent
from mm_a2a.tools.memory import _load_precreated_session, _save_session_data, memorize, get_memory, memorize_list
from config import Config

logger = logging.getLogger(__name__)

# Callback để đảm bảo event loop được quản lý đúng cách
async def ensure_event_loop(context=None, callback_context=None):
    """Đảm bảo event loop được quản lý đúng cách trước khi agent chạy."""
    try:
        # Kiểm tra và khởi tạo event loop nếu cần
        try:
            loop = asyncio.get_running_loop()
            if loop.is_closed():
                logger.warning("Phát hiện event loop đã đóng trong root agent, tạo mới event loop")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            # Không có event loop đang chạy
            logger.info("Không có event loop đang chạy, tạo mới event loop cho root agent")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except Exception as e:
        logger.error(f"Lỗi khi đảm bảo event loop trong root agent: {str(e)}")

# Callback khi agent kết thúc để dọn dẹp tài nguyên
async def cleanup_resources(context=None, callback_context=None):
    """Dọn dẹp tài nguyên khi agent kết thúc."""
    # Sử dụng context hoặc callback_context tùy vào cái nào có sẵn
    ctx = callback_context or context
    
    # Lưu trạng thái session nếu cần
    try:
        if ctx and ctx.session:
            # Lưu thông tin phiên quan trọng vào bộ nhớ lâu dài nếu cần
            session_data = {
                "session_id": ctx.session.session_id,
                "last_interaction": ctx.session.state.get("last_interaction", ""),
                "user_preferences": ctx.session.state.get("user_preferences", {})
            }
            # Lưu thông tin quan trọng vào memory
            await memorize(key="session_info", value=str(session_data))
            logger.info("Đã lưu thông tin phiên làm việc")
    except Exception as e:
        logger.error(f"Lỗi khi dọn dẹp tài nguyên: {str(e)}")

# Khởi tạo Root Agent sử dụng Google Gemini
# Sử dụng Agent để hỗ trợ memory
class RootAgent(Agent):
    name: str = "root_agent"
    description: str = "Root Agent cho MM A2A Ecommerce Chatbot"

# Đảm bảo event loop được thiết lập trước khi khởi tạo agent
try:
    asyncio.get_running_loop()
except RuntimeError:
    # Không có event loop đang chạy
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

root_agent = Agent(
    model="gemini-2.0-flash-001",  # Sử dụng model Gemini-2.0-flash-001
    name="root_agent",
    description="Root Agent cho MM A2A Ecommerce Chatbot",
    instruction=prompt.ROOT_AGENT_INSTR,
    sub_agents=[
        cng_agent,
        # Thêm các sub-agent khác khi cần thiết
    ],
)
