#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API module cho các thao tác liên quan đến xác thực và tài khoản
"""

import logging
from typing import Dict, Any

from .base import APIClientBase

logger = logging.getLogger(__name__)

class AuthAPI(APIClientBase):
    """
    API Client cho các thao tác liên quan đến xác thực và tài khoản.
    """
    
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
    
    async def login_with_mcard(
        self, 
        hash_value: str, 
        store: str, 
        cust_no: str, 
        phone: str, 
        cust_no_mm: str, 
        cust_name: str
    ) -> Dict[str, Any]:
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
    
    async def create_customer_from_mcard(
        self, 
        email: str, 
        firstname: str, 
        lastname: str = "",
        phone: str = "", 
        customer_no: str = "", 
        mcard_no: str = ""
    ) -> Dict[str, Any]:
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
    
    async def get_customer_info(self) -> Dict[str, Any]:
        """
        Lấy thông tin khách hàng hiện tại.
        
        Returns:
            Dict[str, Any]: Thông tin khách hàng.
        """
        graphql_query = """
        query GetCustomerInfo {
          customer {
            firstname
            lastname
            email
            default_shipping
            is_subscribed
            addresses {
              id
              firstname
              lastname
              street
              city
              region {
                region_code
                region
              }
              postcode
              country_code
              telephone
              default_shipping
              default_billing
            }
          }
        }
        """
        
        result = await self.execute_graphql(graphql_query)
        
        if result.get("success", False):
            data = result.get("data", {})
            customer = data.get("customer", {})
            
            if customer:
                return {
                    "success": True,
                    "data": {
                        "customer": customer
                    },
                    "message": "Lấy thông tin khách hàng thành công"
                }
            else:
                return {
                    "success": False,
                    "message": "Không nhận được thông tin khách hàng",
                    "code": "MISSING_CUSTOMER_INFO"
                }
        
        return result
    
    async def check_auth_status(self) -> Dict[str, Any]:
        """
        Kiểm tra trạng thái xác thực của người dùng.
        
        Returns:
            Dict[str, Any]: Kết quả kiểm tra.
        """
        # Thử lấy thông tin khách hàng để kiểm tra token còn hiệu lực không
        result = await self.get_customer_info()
        
        if result.get("success", False):
            return {
                "success": True,
                "is_authenticated": True,
                "message": "Người dùng đã đăng nhập"
            }
        
        # Nếu có lỗi, kiểm tra loại lỗi
        error_code = result.get("code", "")
        if error_code in ["AUTHENTICATION_ERROR", "TOKEN_EXPIRED"]:
            self.clear_auth_token()  # Xóa token nếu đã hết hạn
            return {
                "success": True,
                "is_authenticated": False,
                "message": "Người dùng chưa đăng nhập hoặc phiên đã hết hạn"
            }
        
        # Lỗi khác
        return {
            "success": False,
            "is_authenticated": False,
            "message": result.get("message", "Lỗi kiểm tra trạng thái xác thực"),
            "code": error_code
        } 