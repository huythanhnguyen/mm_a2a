#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API Client cho việc tương tác với API GraphQL của MM Ecommerce
"""

import json
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional, Union, List
from urllib.parse import urljoin

from tenacity import retry, stop_after_attempt, wait_exponential
from config import Config

logger = logging.getLogger(__name__)

class EcommerceAPIClient:
    """
    Client để tương tác với API GraphQL của MM Ecommerce.
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
        self.base_url = base_url.rstrip("/")
        
        if isinstance(timeout, int):
            self.timeout = aiohttp.ClientTimeout(total=timeout)
        elif isinstance(timeout, aiohttp.ClientTimeout):
            self.timeout = timeout
        else:
            self.timeout = aiohttp.ClientTimeout(total=30)  # Default 30s
            
        self._session = None
        self._loop = loop or asyncio.get_event_loop()
        self._auth_token = None
        self._store_code = Config.STORE_CODE
        self._cart_id = None  # Lưu trữ cart ID hiện tại
    
    async def create_session(self) -> aiohttp.ClientSession:
        """
        Tạo một session mới.
        
        Returns:
            aiohttp.ClientSession: Session mới được tạo.
        """
        try:
            # Kiểm tra và lấy event loop hiện tại
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                # Nếu không có loop đang chạy, tạo loop mới
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                
            session = aiohttp.ClientSession(
                timeout=self.timeout,
                loop=self._loop
            )
            return session
        except Exception as e:
            logger.error(f"Lỗi khi tạo session mới: {str(e)}")
            raise
            
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Lấy hoặc tạo một session mới.
        
        Returns:
            aiohttp.ClientSession: Session hiện tại hoặc mới.
        """
        if self._session is None or self._session.closed:
            self._session = await self.create_session()
        return self._session
        
    async def ensure_session(self):
        """Đảm bảo session được khởi tạo và sẵn sàng sử dụng."""
        try:
            if self._session is None or self._session.closed:
                self._session = await self.create_session()
        except Exception as e:
            logger.error(f"Lỗi khi đảm bảo session: {str(e)}")
            raise
    
    async def close(self):
        """Đóng session hiện tại nếu có."""
        if self._session and not self._session.closed:
            try:
                await self._session.close()
            except Exception as e:
                logger.error(f"Lỗi khi đóng session: {str(e)}")
            finally:
                self._session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Tạo headers cho request.
        
        Returns:
            Dict[str, str]: Headers.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Store": self._store_code  # Header Store cho MM Ecommerce
        }
        
        # Thêm token xác thực nếu có
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        
        return headers
    
    def set_auth_token(self, token: str):
        """
        Đặt token xác thực.
        
        Args:
            token: Token xác thực.
        """
        self._auth_token = token
    
    def clear_auth_token(self):
        """Xóa token xác thực."""
        self._auth_token = None
    
    def set_store_code(self, store_code: str):
        """
        Đặt mã cửa hàng.
        
        Args:
            store_code: Mã cửa hàng (ví dụ: b2c_10010_vi).
        """
        self._store_code = store_code
    
    @retry(
        stop=stop_after_attempt(Config.MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=Config.RETRY_DELAY, max=10)
    )
    async def execute_graphql(
        self, 
        query: str, 
        variables: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        method: str = "POST"
    ) -> Dict[str, Any]:
        """
        Thực hiện truy vấn GraphQL.
        
        Args:
            query: Truy vấn GraphQL.
            variables: Biến cho truy vấn (tùy chọn).
            headers: Headers bổ sung (tùy chọn).
            timeout: Timeout cho request (tùy chọn).
            method: Phương thức HTTP, mặc định là POST.
            
        Returns:
            Dict[str, Any]: Kết quả từ API.
            
        Raises:
            Exception: Nếu có lỗi xảy ra.
        """
        _headers = self._get_headers()
        if headers:
            _headers.update(headers)
        
        if timeout:
            _timeout = aiohttp.ClientTimeout(total=timeout)
        else:
            _timeout = self.timeout
        
        # Đảm bảo session được khởi tạo
        try:
            if self._session is None or self._session.closed:
                await self.ensure_session()
                
            # Chuẩn bị payload
            payload = {
                "query": query
            }
            if variables:
                payload["variables"] = variables
                
            url = urljoin(self.base_url, "/graphql")
            
            async with self._session.request(
                method=method,
                url=url,
                json=payload,
                headers=_headers,
                timeout=_timeout
            ) as response:
                result = await self._process_response(response)
                return result
                
        except asyncio.CancelledError:
            # Xử lý khi request bị hủy
            logger.warning("Request bị hủy")
            await self.close()  # Đóng session hiện tại
            raise
            
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện GraphQL request: {str(e)}")
            # Đóng session nếu có lỗi nghiêm trọng
            await self.close()
            return {
                "success": False,
                "message": f"GraphQL Error: {str(e)}",
                "code": "REQUEST_ERROR"
            }
    
    async def _process_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """
        Xử lý response từ API.
        
        Args:
            response: Response từ API.
            
        Returns:
            Dict[str, Any]: Kết quả đã được xử lý.
        """
        if response.status != 200:
            error_text = await response.text()
            logger.error(f"Lỗi HTTP {response.status}: {error_text}")
            return {
                "success": False,
                "message": f"HTTP Error: {response.status}",
                "code": "HTTP_ERROR"
            }
        
        try:
            result = await response.json()
        except Exception as e:
            logger.error(f"Lỗi khi parse JSON response: {str(e)}")
            return {
                "success": False,
                "message": "Invalid JSON response",
                "code": "INVALID_RESPONSE"
            }
        
        if "errors" in result:
            error_message = result["errors"][0].get("message", "Unknown GraphQL error")
            logger.error(f"GraphQL Error: {error_message}")
            return {
                "success": False,
                "message": f"GraphQL Error: {error_message}",
                "code": "GRAPHQL_ERROR"
            }
        
        return {
            "success": True,
            "data": result.get("data", {})
        }
    
    # Các hàm tiện ích cho các API cụ thể
    
    async def search_products(self, query: str, page_size: int = 10, current_page: int = 1) -> Dict[str, Any]:
        """
        Tìm kiếm sản phẩm.
        
        Args:
            query: Từ khóa tìm kiếm.
            page_size: Số lượng sản phẩm trên mỗi trang.
            current_page: Trang hiện tại.
            
        Returns:
            Dict[str, Any]: Kết quả tìm kiếm.
        """
        graphql_query = """
        query ProductSearch($search: String!, $pageSize: Int!, $currentPage: Int!) {
          products(search: $search, pageSize: $pageSize, currentPage: $currentPage, sort: { relevance: DESC }) {
            items {
              id
              sku
              name
              url_key
              price {
                regularPrice {
                  amount {
                    currency
                    value
                  }
                }
              }
              price_range {
                maximum_price {
                  final_price {
                    currency
                    value
                  }
                  discount {
                    amount_off
                    percent_off
                  }
                }
              }
              small_image {
                url
              }
              unit_ecom
              description {
                html
              }
            }
            total_count
          }
        }
        """
        
        variables = {
            "search": query,
            "pageSize": page_size,
            "currentPage": current_page
        }
        
        return await self.execute_graphql(graphql_query, variables, method="POST")
    
    async def get_product_by_sku(self, sku: str) -> Dict[str, Any]:
        """
        Lấy thông tin sản phẩm theo SKU.
        
        Args:
            sku: SKU của sản phẩm.
            
        Returns:
            Dict[str, Any]: Thông tin sản phẩm.
        """
        graphql_query = """
        query GetProductBySku($sku: String!) {
          products(filter: { sku: { eq: $sku } }, pageSize: 1, currentPage: 1) {
            items {
              id
              uid
              sku
              name
              price {
                regularPrice {
                  amount {
                    currency
                    value
                  }
                }
              }
              price_range {
                maximum_price {
                  final_price {
                    currency
                    value
                  }
                  discount {
                    amount_off
                    percent_off
                  }
                }
              }
              media_gallery_entries {
                uid
                label
                position
                disabled
                file
              }
              small_image {
                url
              }
              unit_ecom
              description {
                html
              }
            }
          }
        }
        """
        
        variables = {
            "sku": sku
        }
        
        return await self.execute_graphql(graphql_query, variables, method="POST")
    
    async def get_product_by_art_no(self, art_no: str) -> Dict[str, Any]:
        """
        Lấy thông tin sản phẩm theo Article Number.
        
        Args:
            art_no: Article Number của sản phẩm.
            
        Returns:
            Dict[str, Any]: Thông tin sản phẩm.
        """
        graphql_query = """
        query GetProductByArtNo($artNo: String!) {
          products(filter: { mm_art_no: { eq: $artNo } }) {
            items {
              id
              sku
              name
              url_key
              url_suffix
              price {
                regularPrice {
                  amount {
                    currency
                    value
                  }
                }
              }
              price_range {
                maximum_price {
                  final_price {
                    currency
                    value
                  }
                  discount {
                    amount_off
                    percent_off
                  }
                }
              }
              small_image {
                url
              }
              unit_ecom
              description {
                html
              }
            }
            total_count
          }
        }
        """
        
        variables = {
            "artNo": art_no
        }
        
        return await self.execute_graphql(graphql_query, variables, method="POST")
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Đăng nhập vào hệ thống.
        
        Args:
            email: Email đăng nhập.
            password: Mật khẩu.
            
        Returns:
            Dict[str, Any]: Kết quả đăng nhập.
        """
        graphql_query = """
        mutation GenerateCustomerToken($email: String!, $password: String!) {
          generateCustomerToken(
            email: $email,
            password: $password
          ) {
            token
          }
        }
        """
        
        variables = {
            "email": email,
            "password": password
        }
        
        result = await self.execute_graphql(graphql_query, variables)
        
        if result.get("success", False):
            data = result.get("data", {})
            token = data.get("generateCustomerToken", {}).get("token")
            
            if token:
                # Lưu token xác thực
                self.set_auth_token(token)
                
                return {
                    "success": True,
                    "message": "Đăng nhập thành công",
                    "token": token
                }
            else:
                return {
                    "success": False,
                    "message": "Không nhận được token xác thực",
                    "code": "MISSING_TOKEN"
                }
        
        return result
    
    async def create_cart(self, is_guest: bool = False) -> Dict[str, Any]:
        """
        Tạo giỏ hàng mới.
        
        Args:
            is_guest: Có phải khách vãng lai không.
            
        Returns:
            Dict[str, Any]: Kết quả tạo giỏ hàng.
        """
        graphql_query = """
        mutation CreateEmptyCart($is_guest: Boolean!) {
          createEmptyCart(
            input: { is_guest_cart: $is_guest }
          )
        }
        """
        
        variables = {
            "is_guest": is_guest
        }
        
        try:
            # Đảm bảo có session mới
            await self.ensure_session()
            
            result = await self.execute_graphql(graphql_query, variables, method="POST")
            
            if result.get("success", False):
                data = result.get("data", {})
                cart_id = data.get("createEmptyCart")
                
                if cart_id:
                    # Lưu cart_id vào session
                    self._cart_id = cart_id
                    
                    return {
                        "success": True,
                        "cart_id": cart_id,
                        "message": "Tạo giỏ hàng thành công"
                    }
                else:
                    return {
                        "success": False,
                        "message": "Không nhận được cart ID",
                        "code": "MISSING_CART_ID"
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo giỏ hàng: {str(e)}")
            # Thử tạo session mới nếu có lỗi
            try:
                await self.close()  # Đóng session cũ
                await self.ensure_session()  # Tạo session mới
                return await self.create_cart(is_guest)  # Thử lại
            except Exception as e2:
                logger.error(f"Lỗi khi thử lại tạo giỏ hàng: {str(e2)}")
                return {
                    "success": False,
                    "message": f"Error creating cart: {str(e2)}",
                    "code": "CART_ERROR"
                }
    
    async def add_to_cart(
        self,
        cart_id: Optional[str],
        product_id: str,
        quantity: int = 1,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Thêm sản phẩm vào giỏ hàng với xử lý lỗi nâng cao.
        
        Args:
            cart_id: ID của giỏ hàng (tùy chọn).
            product_id: Article Number (art_no) của sản phẩm.
            quantity: Số lượng sản phẩm.
            retry_count: Số lần thử lại tối đa khi gặp lỗi.
            
        Returns:
            Dict[str, Any]: Kết quả thêm sản phẩm.
        """
        graphql_query = """
        mutation AddProductsToCart($cartId: String!, $items: [CartItemInput!]!) {
            addProductsToCart(
                cartId: $cartId,
                use_art_no: true,
                cartItems: $items
            ) {
                cart {
                    id
                    email
                    is_guest
                    itemsV2 {
                        items {
                            id
                            product {
                                name
                                sku
                                small_image {
                                    url
                                }
                            }
                            quantity
                            prices {
                                price {
                                    value
                                    currency
                                }
                                row_total {
                                    value
                                    currency
                                }
                            }
                        }
                        total_quantity
                    }
                    prices {
                        grand_total {
                            value
                            currency
                        }
                    }
                }
                user_errors {
                    code
                    message
                }
            }
        }
        """
        
        async def _try_add_to_cart(cart_id: str) -> Dict[str, Any]:
            """Helper function để thử thêm sản phẩm vào giỏ hàng."""
            variables = {
                "cartId": cart_id,
                "items": [
                    {
                        "quantity": quantity,
                        "sku": product_id
                    }
                ]
            }
            
            return await self.execute_graphql(graphql_query, variables)
        
        try:
            # Đảm bảo có session
            await self.ensure_session()
            
            # Sử dụng cart_id từ tham số hoặc từ session
            target_cart_id = cart_id or self._cart_id
            
            # Nếu không có giỏ hàng, tạo mới
            if not target_cart_id:
                create_result = await self.create_cart(is_guest=True)
                if not create_result.get("success", False):
                    return create_result
                target_cart_id = create_result.get("cart_id")
                self._cart_id = target_cart_id
            
            # Thử thêm sản phẩm với số lần thử lại
            for attempt in range(retry_count):
                result = await _try_add_to_cart(target_cart_id)
                
                if result.get("success", False):
                    data = result.get("data", {})
                    add_result = data.get("addProductsToCart", {})
                    user_errors = add_result.get("user_errors", [])
                    
                    if not user_errors:
                        cart = add_result.get("cart", {})
                        # Cập nhật cart_id trong session
                        self._cart_id = cart.get("id")
                        
                        return {
                            "success": True,
                            "message": "Thêm sản phẩm vào giỏ hàng thành công",
                            "data": {
                                "cart": cart
                            }
                        }
                    else:
                        error = user_errors[0]
                        error_code = error.get("code", "UNKNOWN_ERROR")
                        error_message = error.get("message", "Unknown error")
                        
                        # Xử lý các trường hợp lỗi cụ thể
                        if error_code == "CART_NOT_FOUND" and attempt < retry_count - 1:
                            # Tạo giỏ hàng mới và thử lại
                            create_result = await self.create_cart(is_guest=True)
                            if create_result.get("success", False):
                                target_cart_id = create_result.get("cart_id")
                                self._cart_id = target_cart_id
                                continue
                        
                        elif error_code == "PRODUCT_NOT_FOUND":
                            # Thử tìm sản phẩm bằng SKU
                            product_result = await self.get_product_by_sku(product_id)
                            if product_result.get("success", False):
                                product = product_result.get("data", {}).get("products", {}).get("items", [])
                                if product:
                                    # Thử lại với SKU mới
                                    product_id = product[0].get("sku")
                                    continue
                        
                        return {
                            "success": False,
                            "message": error_message,
                            "code": error_code
                        }
                
                # Nếu có lỗi khác, thử lại sau một khoảng thời gian
                if attempt < retry_count - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # Tăng thời gian chờ mỗi lần thử
            
            return {
                "success": False,
                "message": "Không thể thêm sản phẩm vào giỏ hàng sau nhiều lần thử",
                "code": "MAX_RETRIES_EXCEEDED"
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi thêm sản phẩm vào giỏ hàng: {str(e)}")
            return {
                "success": False,
                "message": f"Error adding product to cart: {str(e)}",
                "code": "ADD_TO_CART_ERROR"
            }
    
    async def login_with_mcard(self, hash_value: str, store: str, cust_no: str, 
                               phone: str, cust_no_mm: str, cust_name: str) -> Dict[str, Any]:
        """
        Đăng nhập bằng thông tin MCard.
        
        Args:
            hash_value: Giá trị hash.
            store: Mã cửa hàng.
            cust_no: Mã khách hàng.
            phone: Số điện thoại.
            cust_no_mm: Mã khách hàng MM.
            cust_name: Tên khách hàng.
            
        Returns:
            Dict[str, Any]: Kết quả đăng nhập.
        """
        graphql_query = """
        mutation generateLoginMcardInfo($input: GenerateLoginMcardInfoInput) {
          generateLoginMcardInfo(input: $input) {
            customer_token
            store_view_code
          }
        }
        """
        
        variables = {
            "input": {
                "hash": hash_value,
                "store": store,
                "cust_no": cust_no,
                "phone": phone,
                "cust_no_mm": cust_no_mm,
                "cust_name": cust_name
            }
        }
        
        result = await self.execute_graphql(graphql_query, variables)
        
        if result.get("success", False):
            data = result.get("data", {})
            login_info = data.get("generateLoginMcardInfo", {})
            token = login_info.get("customer_token")
            store_view_code = login_info.get("store_view_code")
            
            if token:
                # Lưu token xác thực và mã cửa hàng
                self.set_auth_token(token)
                self.set_store_code(store_view_code)
                
                return {
                    "success": True,
                    "message": "Đăng nhập thành công",
                    "token": token,
                    "store_view_code": store_view_code
                }
            elif login_info is not None:
                # Trường hợp token là null nhưng có store_view_code - chưa có tài khoản
                return {
                    "success": False,
                    "message": "Chưa có tài khoản",
                    "code": "NO_ACCOUNT",
                    "store_view_code": store_view_code
                }
            else:
                return {
                    "success": False,
                    "message": "Không nhận được thông tin đăng nhập",
                    "code": "MISSING_LOGIN_INFO"
                }
        
        return result
    
    async def create_customer_from_mcard(self, email: str, firstname: str, lastname: str = "",
                                        phone: str = "", customer_no: str = "", mcard_no: str = "") -> Dict[str, Any]:
        """
        Tạo tài khoản khách hàng từ thông tin MCard.
        
        Args:
            email: Email khách hàng.
            firstname: Tên khách hàng.
            lastname: Họ khách hàng.
            phone: Số điện thoại.
            customer_no: Mã khách hàng.
            mcard_no: Mã MCard.
            
        Returns:
            Dict[str, Any]: Kết quả tạo tài khoản.
        """
        graphql_query = """
        mutation createCustomerFromMcard($input: CustomerCreateInput!) {
          createCustomerFromMcard(input: $input) {
            customer_token
            customer {
              email
              firstname
            }
          }
        }
        """
        
        variables = {
            "input": {
                "email": email,
                "firstname": firstname,
                "lastname": lastname,
                "is_subscribed": False,
                "custom_attributes": [
                    {
                        "attribute_code": "company_user_phone_number",
                        "value": phone
                    },
                    {
                        "attribute_code": "customer_no",
                        "value": customer_no
                    },
                    {
                        "attribute_code": "mcard_no",
                        "value": mcard_no
                    }
                ]
            }
        }
        
        result = await self.execute_graphql(graphql_query, variables)
        
        if result.get("success", False):
            data = result.get("data", {})
            create_result = data.get("createCustomerFromMcard", {})
            token = create_result.get("customer_token")
            customer = create_result.get("customer", {})
            
            if token:
                # Lưu token xác thực
                self.set_auth_token(token)
                
                return {
                    "success": True,
                    "message": "Tạo tài khoản thành công",
                    "token": token,
                    "customer": customer
                }
            else:
                return {
                    "success": False,
                    "message": "Không nhận được token xác thực",
                    "code": "MISSING_TOKEN"
                }
        
        return result
    
    async def get_token_lifetime(self) -> Dict[str, Any]:
        """
        Lấy thời gian sống của token.
        
        Returns:
            Dict[str, Any]: Kết quả với thời gian sống của token.
        """
        graphql_query = """
        query GetStoreConfigData {
          storeConfig {
            customer_access_token_lifetime
          }
        }
        """
        
        result = await self.execute_graphql(graphql_query, method="POST")
        
        if result.get("success", False):
            data = result.get("data", {})
            store_config = data.get("storeConfig", {})
            lifetime = store_config.get("customer_access_token_lifetime")
            
            if lifetime is not None:
                return {
                    "success": True,
                    "message": "Lấy thời gian sống của token thành công",
                    "lifetime_hours": lifetime
                }
            else:
                return {
                    "success": False,
                    "message": "Không nhận được thời gian sống của token",
                    "code": "MISSING_LIFETIME"
                }
        
        return result
    
    async def search_multiple_products(
        self,
        keywords: List[str],
        filters: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, str]] = None,
        combine_mode: str = "union",
        page_size: int = 10,
        current_page: int = 1
    ) -> Dict[str, Any]:
        """
        Tìm kiếm nhiều từ khóa sản phẩm cùng lúc với các tùy chọn nâng cao.
        
        Args:
            keywords: Danh sách các từ khóa tìm kiếm.
            filters: Các bộ lọc chung cho tất cả từ khóa.
            sort: Tiêu chí sắp xếp kết quả.
            combine_mode: Cách kết hợp kết quả ("union" hoặc "intersection").
            page_size: Số lượng sản phẩm trên mỗi trang.
            current_page: Trang hiện tại.
            
        Returns:
            Dict[str, Any]: Kết quả tìm kiếm gộp lại.
        """
        results = []
        total_count = 0
        seen_ids = set()
        
        try:
            # Tìm kiếm song song cho tất cả từ khóa
            search_tasks = []
            for keyword in keywords:
                task = asyncio.create_task(
                    self.suggest_products(
                        base_query=keyword,
                        filters=filters,
                        sort=sort,
                        page_size=page_size,
                        current_page=current_page
                    )
                )
                search_tasks.append(task)
            
            # Chờ tất cả tìm kiếm hoàn thành
            search_results = await asyncio.gather(*search_tasks)
            
            # Xử lý kết quả theo combine_mode
            if combine_mode == "intersection":
                # Chỉ giữ lại sản phẩm xuất hiện trong TẤT CẢ từ khóa
                product_sets = []
                for result in search_results:
                    if result.get("success", False):
                        products = result.get("data", {}).get("products", {})
                        items = products.get("items", [])
                        product_ids = {item["id"] for item in items}
                        product_sets.append(product_ids)
                
                if product_sets:
                    common_ids = set.intersection(*product_sets)
                    # Lấy thông tin sản phẩm từ ID chung
                    for result in search_results:
                        if result.get("success", False):
                            products = result.get("data", {}).get("products", {})
                            items = products.get("items", [])
                            for item in items:
                                if item["id"] in common_ids and item["id"] not in seen_ids:
                                    results.append(item)
                                    seen_ids.add(item["id"])
                                    total_count += 1
            else:  # union mode
                # Gộp tất cả sản phẩm, loại bỏ trùng lặp
                for result in search_results:
                    if result.get("success", False):
                        products = result.get("data", {}).get("products", {})
                        items = products.get("items", [])
                        for item in items:
                            if item["id"] not in seen_ids:
                                results.append(item)
                                seen_ids.add(item["id"])
                                total_count += 1
            
            # Sắp xếp kết quả cuối cùng nếu cần
            if sort:
                results.sort(
                    key=lambda x: (
                        x.get("price", {}).get("regularPrice", {}).get("amount", {}).get("value", 0)
                        if sort.get("price") == "ASC"
                        else -x.get("price", {}).get("regularPrice", {}).get("amount", {}).get("value", 0)
                        if sort.get("price") == "DESC"
                        else 0
                    )
                )
            
            # Phân trang kết quả
            start_idx = (current_page - 1) * page_size
            end_idx = start_idx + page_size
            paged_results = results[start_idx:end_idx]
            
            return {
                "success": True,
                "data": {
                    "products": {
                        "items": paged_results,
                        "total_count": total_count,
                        "page_info": {
                            "page_size": page_size,
                            "current_page": current_page,
                            "total_pages": (total_count + page_size - 1) // page_size
                        }
                    }
                },
                "message": f"Tìm thấy {total_count} sản phẩm phù hợp"
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm nhiều từ khóa: {str(e)}")
            return {
                "success": False,
                "message": f"Error searching multiple keywords: {str(e)}",
                "code": "SEARCH_ERROR"
            }
    
    async def suggest_products(
        self,
        base_query: str,
        filters: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, str]] = None,
        page_size: int = 10,
        current_page: int = 1
    ) -> Dict[str, Any]:
        """
        Đề xuất sản phẩm dựa trên query gốc với các bộ lọc và sắp xếp.
        
        Args:
            base_query: Query tìm kiếm cơ bản.
            filters: Các bộ lọc (giá, danh mục, thương hiệu...).
            sort: Tiêu chí sắp xếp (giá, mới nhất, bán chạy...).
            page_size: Số lượng sản phẩm trên mỗi trang.
            current_page: Trang hiện tại.
            
        Returns:
            Dict[str, Any]: Kết quả đề xuất sản phẩm.
        """
        graphql_query = """
        query SuggestProducts(
            $search: String!,
            $filters: ProductAttributeFilterInput,
            $sort: ProductAttributeSortInput,
            $pageSize: Int!,
            $currentPage: Int!
        ) {
            products(
                search: $search,
                filter: $filters,
                sort: $sort,
                pageSize: $pageSize,
                currentPage: $currentPage
            ) {
                items {
                    id
                    sku
                    name
                    url_key
                    price {
                        regularPrice {
                            amount {
                                currency
                                value
                            }
                        }
                    }
                    price_range {
                        maximum_price {
                            final_price {
                                currency
                                value
                            }
                            discount {
                                amount_off
                                percent_off
                            }
                        }
                    }
                    small_image {
                        url
                    }
                    unit_ecom
                    description {
                        html
                    }
                    categories {
                        id
                        name
                        url_key
                    }
                    brand
                    new_from_date
                    special_from_date
                }
                total_count
                page_info {
                    page_size
                    current_page
                    total_pages
                }
                aggregations {
                    attribute_code
                    count
                    label
                    options {
                        label
                        value
                        count
                    }
                }
            }
        }
        """
        
        variables = {
            "search": base_query,
            "pageSize": page_size,
            "currentPage": current_page
        }
        
        if filters:
            variables["filters"] = filters
        
        if sort:
            variables["sort"] = sort
        
        try:
            result = await self.execute_graphql(graphql_query, variables)
            
            if result.get("success", False):
                data = result.get("data", {})
                products = data.get("products", {})
                
                # Thêm các gợi ý điều chỉnh tìm kiếm
                search_suggestions = []
                aggregations = products.get("aggregations", [])
                
                for agg in aggregations:
                    if agg["count"] > 0:
                        search_suggestions.append({
                            "type": agg["attribute_code"],
                            "label": agg["label"],
                            "options": agg["options"]
                        })
                
                return {
                    "success": True,
                    "data": {
                        "products": products,
                        "suggestions": search_suggestions
                    }
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi đề xuất sản phẩm: {str(e)}")
            return {
                "success": False,
                "message": f"Error suggesting products: {str(e)}",
                "code": "SUGGESTION_ERROR"
            }
    
    async def get_cart_info(self, cart_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Lấy thông tin chi tiết về giỏ hàng.
        
        Args:
            cart_id: ID của giỏ hàng (tùy chọn, mặc định sử dụng cart_id hiện tại).
            
        Returns:
            Dict[str, Any]: Thông tin giỏ hàng.
        """
        graphql_query = """
        query GetCartInfo($cartId: String!) {
            cart(cart_id: $cartId) {
                id
                email
                is_guest
                itemsV2 {
                    items {
                        id
                        product {
                            id
                            name
                            sku
                            small_image {
                                url
                            }
                            price {
                                regularPrice {
                                    amount {
                                        value
                                        currency
                                    }
                                }
                            }
                        }
                        quantity
                        prices {
                            price {
                                value
                                currency
                            }
                            row_total {
                                value
                                currency
                            }
                            total_item_discount {
                                value
                                currency
                            }
                        }
                    }
                    total_quantity
                }
                prices {
                    subtotal_excluding_tax {
                        value
                        currency
                    }
                    subtotal_including_tax {
                        value
                        currency
                    }
                    applied_taxes {
                        amount {
                            value
                            currency
                        }
                        label
                    }
                    discounts {
                        amount {
                            value
                            currency
                        }
                        label
                    }
                    grand_total {
                        value
                        currency
                    }
                }
                available_payment_methods {
                    code
                    title
                }
                shipping_addresses {
                    available_shipping_methods {
                        carrier_code
                        carrier_title
                        method_code
                        method_title
                        price_incl_tax {
                            value
                            currency
                        }
                    }
                }
            }
        }
        """
        
        try:
            target_cart_id = cart_id or self._cart_id
            if not target_cart_id:
                # Tạo giỏ hàng mới nếu chưa có
                create_result = await self.create_cart(is_guest=True)
                if not create_result.get("success", False):
                    return create_result
                target_cart_id = create_result.get("cart_id")
                self._cart_id = target_cart_id
            
            variables = {
                "cartId": target_cart_id
            }
            
            result = await self.execute_graphql(graphql_query, variables)
            
            if result.get("success", False):
                data = result.get("data", {})
                cart = data.get("cart", {})
                
                if not cart:
                    # Giỏ hàng không tồn tại hoặc đã hết hạn
                    self._cart_id = None  # Reset cart_id
                    return {
                        "success": False,
                        "message": "Giỏ hàng không tồn tại hoặc đã hết hạn",
                        "code": "CART_NOT_FOUND"
                    }
                
                # Cập nhật cart_id trong session
                self._cart_id = cart.get("id")
                
                return {
                    "success": True,
                    "data": {
                        "cart": cart
                    },
                    "message": "Lấy thông tin giỏ hàng thành công"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin giỏ hàng: {str(e)}")
            return {
                "success": False,
                "message": f"Error getting cart info: {str(e)}",
                "code": "CART_ERROR"
            }