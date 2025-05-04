#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API Client chính cho việc tương tác với API GraphQL của MM Ecommerce.
Kết hợp các module client chuyên biệt.
"""

import logging
from typing import Optional, Union, Any, Dict
import aiohttp
import asyncio

from .base import APIClientBase

logger = logging.getLogger(__name__)

class EcommerceAPIClient(APIClientBase):
    """
    Client tổng hợp để tương tác với API GraphQL của MM Ecommerce.
    Sử dụng các module API chuyên biệt thông qua composition thay vì kế thừa.
    """
    
    def __init__(
        self,
        base_url: str,
        timeout: Optional[Union[int, aiohttp.ClientTimeout]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        """
        Khởi tạo API client.
        
        Args:
            base_url: URL cơ sở của API.
            timeout: Timeout cho requests, có thể là số giây hoặc ClientTimeout object.
            loop: Event loop tùy chọn, mặc định sẽ lấy loop hiện tại.
        """
        # Khởi tạo lớp cơ sở
        super().__init__(base_url, timeout, loop)
        
        # Import các module API ở đây để tránh vòng lặp import
        from .product import ProductAPI
        from .cart import CartAPI
        from .auth import AuthAPI
        
        # Tạo các instance của các module API
        self._product_api = ProductAPI(base_url, timeout, loop)
        self._cart_api = CartAPI(base_url, timeout, loop)
        self._auth_api = AuthAPI(base_url, timeout, loop)
    
    async def ensure_session(self):
        """Đảm bảo session được khởi tạo và đồng bộ giữa các API module."""
        await super().ensure_session()
        await self._product_api.ensure_session()
        await self._cart_api.ensure_session()
        await self._auth_api.ensure_session()
    
    async def close(self):
        """Đóng tất cả các session."""
        await super().close()
        await self._product_api.close()
        await self._cart_api.close()
        await self._auth_api.close()
    
    def set_auth_token(self, token: str):
        """Đồng bộ token xác thực cho tất cả các API module."""
        super().set_auth_token(token)
        self._product_api.set_auth_token(token)
        self._cart_api.set_auth_token(token)
        self._auth_api.set_auth_token(token)
    
    def set_store_code(self, store_code: str):
        """Đồng bộ mã cửa hàng cho tất cả các API module."""
        super().set_store_code(store_code)
        self._product_api.set_store_code(store_code)
        self._cart_api.set_store_code(store_code)
        self._auth_api.set_store_code(store_code)
    
    # Định nghĩa lại các phương thức của các API module
    # Các phương thức Product API
    async def search_products(self, query: str, page_size: int = 10, current_page: int = 1):
        return await self._product_api.search_products(query, page_size, current_page)
    
    async def get_product_by_sku(self, sku: str):
        return await self._product_api.get_product_by_sku(sku)
    
    async def get_product_by_art_no(self, art_no: str):
        return await self._product_api.get_product_by_art_no(art_no)
    
    async def suggest_products(self, base_query: str, filters=None, sort=None, page_size=10, current_page=1):
        return await self._product_api.suggest_products(base_query, filters, sort, page_size, current_page)
    
    async def search_multiple_products(self, keywords, filters=None, sort=None, combine_mode="union", page_size=10, current_page=1):
        return await self._product_api.search_multiple_products(keywords, filters, sort, combine_mode, page_size, current_page)
    
    # Các phương thức Cart API
    async def create_cart(self, is_guest=False):
        cart_result = await self._cart_api.create_cart(is_guest)
        if cart_result.get("success", False):
            self._cart_id = cart_result.get("cart_id")
        return cart_result
    
    async def add_to_cart(self, cart_id=None, product_id=None, quantity=1, retry_count=3):
        return await self._cart_api.add_to_cart(cart_id or self._cart_id, product_id, quantity, retry_count)
    
    async def get_cart_info(self, cart_id=None):
        return await self._cart_api.get_cart_info(cart_id or self._cart_id)
    
    async def update_cart_item(self, cart_id=None, cart_item_id=None, quantity=1):
        return await self._cart_api.update_cart_item(cart_id or self._cart_id, cart_item_id, quantity)
    
    async def remove_cart_item(self, cart_id=None, cart_item_id=None):
        return await self._cart_api.remove_cart_item(cart_id or self._cart_id, cart_item_id)
    
    # Các phương thức Auth API
    async def login(self, email, password):
        login_result = await self._auth_api.login(email, password)
        if login_result.get("success", False):
            token = login_result.get("token")
            if token:
                self.set_auth_token(token)
        return login_result
    
    async def login_with_mcard(self, hash_value, store, cust_no, phone, cust_no_mm, cust_name):
        login_result = await self._auth_api.login_with_mcard(hash_value, store, cust_no, phone, cust_no_mm, cust_name)
        if login_result.get("success", False):
            token = login_result.get("token")
            store_view_code = login_result.get("store_view_code")
            if token:
                self.set_auth_token(token)
            if store_view_code:
                self.set_store_code(store_view_code)
        return login_result
    
    async def create_customer_from_mcard(self, email, firstname, lastname="", phone="", customer_no="", mcard_no=""):
        return await self._auth_api.create_customer_from_mcard(email, firstname, lastname, phone, customer_no, mcard_no)
    
    async def get_token_lifetime(self):
        return await self._auth_api.get_token_lifetime()
    
    async def get_customer_info(self):
        return await self._auth_api.get_customer_info()
    
    async def check_auth_status(self):
        return await self._auth_api.check_auth_status()
    
    # Phương thức kiểm tra kết nối
    async def ping(self) -> Dict[str, Any]:
        """
        Kiểm tra kết nối với API.
        
        Returns:
            Dict[str, Any]: Kết quả kiểm tra kết nối.
        """
        try:
            # Sử dụng truy vấn GraphQL đơn giản để kiểm tra kết nối
            graphql_query = """
            query {
              storeConfig {
                store_code
              }
            }
            """
            
            await self.ensure_session()
            result = await self.execute_graphql(graphql_query)
            
            if result.get("success", False):
                return {
                    "success": True,
                    "message": "Kết nối đến API thành công",
                    "data": result.get("data", {})
                }
            else:
                return {
                    "success": False,
                    "message": "Không thể kết nối đến API",
                    "error": result.get("message", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"Lỗi khi ping API: {str(e)}")
            return {
                "success": False,
                "message": f"Error pinging API: {str(e)}"
            } 