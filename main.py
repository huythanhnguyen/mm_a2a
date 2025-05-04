#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2025
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
MM A2A Ecommerce Chatbot - Điểm khởi chạy chính
"""

import argparse
import logging
import os
import uuid
import time
import asyncio
import signal
from mm_a2a.agent.agent import root_agent
from mm_a2a.tools.api_client import EcommerceAPIClient
from config import Config

# Thiết lập locale và encoding
import sys
import locale

# Import thư viện cần thiết cho Google ADK
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Thiết lập encoding
locale.setlocale(locale.LC_ALL, '')
sys.stdout.reconfigure(encoding='utf-8')

# Thiết lập logging với UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Sử dụng stdout với encoding UTF-8
        logging.FileHandler("mm_a2a.log", encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

# Biến global để theo dõi trạng thái event loop
main_loop = None
is_shutting_down = False

def setup_environment():
    """Thiết lập môi trường chạy"""
    # Kiểm tra API key
    if not os.environ.get("GOOGLE_API_KEY"):
        logger.warning("GOOGLE_API_KEY not found in environment variables.")
        api_key = os.getenv("GOOGLE_API_KEY", Config.DEFAULT_API_KEY)
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not configured.")
        os.environ["GOOGLE_API_KEY"] = api_key

    # Thiết lập các biến môi trường khác nếu cần
    os.environ["MM_ECOMMERCE_API_URL"] = os.getenv("MM_ECOMMERCE_API_URL", Config.API_BASE_URL)

def cleanup_resources():
    """Dọn dẹp tài nguyên trước khi thoát"""
    global is_shutting_down
    is_shutting_down = True
    logger.info("Đang dọn dẹp tài nguyên...")
    
    # Đóng các API client nếu có
    try:
        from mm_a2a.sub_agents.cng.agent import api_client
        if api_client:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.run_until_complete(api_client.close())
    except Exception as e:
        logger.error(f"Lỗi khi đóng API client: {str(e)}")
    
    # Đóng các event loop đang chạy
    global main_loop
    if main_loop and not main_loop.is_closed():
        try:
            # Hủy tất cả các task đang chạy
            pending = asyncio.all_tasks(main_loop)
            for task in pending:
                task.cancel()
                
            # Chạy loop một lần cuối để xử lý hủy
            main_loop.run_until_complete(asyncio.sleep(0.1))
            main_loop.close()
        except Exception as e:
            logger.error(f"Lỗi khi đóng event loop: {str(e)}")
    
    logger.info("Đã hoàn tất dọn dẹp tài nguyên")

def signal_handler(sig, frame):
    """Xử lý tín hiệu kết thúc từ hệ thống"""
    print("\nĐang dừng chatbot...")
    cleanup_resources()
    sys.exit(0)

# Đăng ký handler xử lý tín hiệu kết thúc
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def start_cli():
    """Khởi chạy phiên bản CLI của chatbot"""
    global main_loop
    logger.info("Starting MM A2A Ecommerce Chatbot (CLI)...")
    print("=== MM A2A Ecommerce Chatbot ===")
    print("Type 'exit', 'quit', or 'q' to exit.")
    
    # Thiết lập Runner API
    session_service = InMemorySessionService()
    APP_NAME = "mm_a2a_ecommerce"
    USER_ID = str(uuid.uuid4())
    SESSION_ID = str(uuid.uuid4())
    
    # Tạo phiên mới
    session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    
    # Tạo runner
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    # Tạo event loop riêng cho CLI
    main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(main_loop)
    
    try:
        while not is_shutting_down:
            user_input = input("\nYou: ")
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break
            
            try:
                # Tạo nội dung người dùng
                user_content = types.Content(role='user', parts=[types.Part(text=user_input)])
                
                # Biến để lưu phản hồi cuối cùng
                final_response = None
                
                # Kiểm tra và tạo mới event loop nếu cần
                if main_loop.is_closed():
                    logger.warning("Event loop đã đóng, tạo mới event loop")
                    main_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(main_loop)
                
                # Chạy agent thông qua runner
                try:
                    # Sử dụng asyncio.run trong CLI để đảm bảo event loop được quản lý đúng
                    for event in runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=user_content):
                        if event.is_final_response() and event.content and event.content.parts:
                            final_response = event.content.parts[0].text
                    
                    # Đảm bảo tất cả task bất đồng bộ được hoàn thành
                    # Nhưng với timeout ngắn để tránh treo
                    try:
                        main_loop.run_until_complete(asyncio.sleep(0.1))
                    except Exception as e:
                        logger.warning(f"Lỗi khi chờ hoàn thành tasks: {str(e)}")
                    
                except Exception as run_error:
                    logger.error(f"Error running agent: {str(run_error)}")
                    
                    # Kiểm tra nếu lỗi liên quan đến event loop
                    if "event loop" in str(run_error).lower():
                        logger.warning("Phát hiện lỗi event loop, đang thử khởi tạo lại...")
                        
                        # Tạo mới event loop
                        if not main_loop.is_closed():
                            main_loop.close()
                        main_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(main_loop)
                        
                        # Thử lại
                        try:
                            for event in runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=user_content):
                                if event.is_final_response() and event.content and event.content.parts:
                                    final_response = event.content.parts[0].text
                        except Exception as retry_error:
                            logger.error(f"Lỗi khi thử lại sau khi khởi tạo event loop mới: {str(retry_error)}")
                            final_response = "Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu của bạn."
                    else:
                        final_response = "Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu của bạn."
                
                # In phản hồi
                if final_response:
                    print(f"\nChatbot: {final_response}")
                else:
                    print("\nChatbot: Xin lỗi, tôi không thể xử lý yêu cầu của bạn lúc này.")
                    
                # Ngắn nghỉ để đảm bảo tất cả các tasks không đồng bộ đã hoàn thành
                time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                print("\nChatbot: Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu của bạn.")
    
    finally:
        # Đảm bảo các tài nguyên được giải phóng
        cleanup_resources()

def main():
    """Main function of the application"""
    parser = argparse.ArgumentParser(description="MM A2A Ecommerce Chatbot")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    parser.add_argument("--api", action="store_true", help="Run chatbot as an API server")
    args = parser.parse_args()
    
    # Set logging level based on debug mode
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Running in debug mode")
    
    try:
        # Setup environment
        setup_environment()
        
        # Start application according to mode
        if args.api:
            # Import here to avoid unnecessary imports when running in CLI mode
            from app import start_server
            start_server()
        else:
            start_cli()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        # Đảm bảo tài nguyên được giải phóng dù có lỗi
        cleanup_resources()

if __name__ == "__main__":
    main()