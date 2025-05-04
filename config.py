#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cấu hình cho MM A2A Ecommerce Chatbot
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any, List

# Tải biến môi trường từ file .env (nếu có)
load_dotenv()

class Config:
    """Cấu hình chung cho ứng dụng."""
    
    # Cấu hình API
    API_BASE_URL = "https://online.mmvietnam.com/graphql"
    API_TIMEOUT = 30  # Timeout mặc định 30 giây
    
    # Store code
    STORE_CODE = "b2c_10010_vi"
    
    # Headers mặc định cho API
    DEFAULT_HEADERS: Dict[str, Any] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Store": STORE_CODE
    }
    
    # Cấu hình retry
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # Delay giữa các lần retry (giây)
    MAX_RETRY_ATTEMPTS = 3
    
    # Cấu hình logging
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Các mã lỗi cần retry
    RETRY_ERROR_CODES = [
        "HTTP_ERROR",
        "TIMEOUT",
        "CONNECTION_ERROR",
        "NETWORK_ERROR"
    ]
    
    # URL dự phòng
    FALLBACK_API_URL = "https://online.mmvietnam.com/graphql"
    
    # Thêm các thuộc tính cho backend server và API
    DEFAULT_API_KEY = os.getenv("GOOGLE_API_KEY", "demo-key")
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", 5000))
    
    # Dải cổng server có thể sử dụng nếu cổng mặc định đã được sử dụng
    PORT_RANGE: List[int] = [5000, 5001, 5002, 5003, 5004, 5005]
    
    # GraphQL queries mẫu (có thể mở rộng tuỳ hệ thống)
    GRAPHQL_QUERIES = {
        "create_guest_cart": """
        mutation {
          createGuestCart {
            cart {
              id
            }
          }
        }
        """,
        "create_empty_cart": """
        mutation CreateCartAfterSignIn {
          cartId: createEmptyCart
        }
        """
    }
    
    @classmethod
    def get_api_url(cls) -> str:
        """Trả về URL API, thử URL dự phòng nếu URL chính không hoạt động."""
        return cls.API_BASE_URL or cls.FALLBACK_API_URL
    
    @classmethod
    def get_headers(cls) -> Dict[str, Any]:
        """Trả về headers mặc định cho API."""
        return cls.DEFAULT_HEADERS.copy()  # Trả về bản sao để tránh thay đổi headers gốc

class DevelopmentConfig(Config):
    """Cấu hình cho môi trường phát triển"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    
class ProductionConfig(Config):
    """Cấu hình cho môi trường sản xuất"""
    DEBUG = False
    LOG_LEVEL = "INFO"
    
class TestingConfig(Config):
    """Cấu hình cho môi trường kiểm thử"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    API_BASE_URL = "https://online.mmvietnam.com/graphql"
    
# Chọn cấu hình dựa trên biến môi trường
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig
}

# Mặc định sử dụng cấu hình development
active_config = config_map.get(os.getenv("ENV", "development").lower(), DevelopmentConfig)