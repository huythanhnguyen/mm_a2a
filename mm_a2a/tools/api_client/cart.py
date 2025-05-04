#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API module cho các thao tác liên quan đến giỏ hàng
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List

from .base import APIClientBase
from config import Config

logger = logging.getLogger(__name__)

class CartAPI(APIClientBase):
    """
    API Client cho các thao tác liên quan đến giỏ hàng.
    """
    
    async def create_cart(self, is_guest: bool = False) -> Dict[str, Any]:
        """
        Tạo giỏ hàng mới.
        
        Args:
            is_guest: Có phải khách vãng lai không.
            
        Returns:
            Dict[str, Any]: Kết quả tạo giỏ hàng.
        """
        if is_guest:
            # Giỏ hàng khách vãng lai
            graphql_query = Config.GRAPHQL_QUERIES.get("create_guest_cart", """
            mutation {
              createGuestCart {
                cart {
                  id
                }
              }
            }
            """)
            variables = {}
        else:
            # Giỏ hàng thường
            graphql_query = Config.GRAPHQL_QUERIES.get("create_empty_cart", """
            mutation CreateCartAfterSignIn {
              cartId: createEmptyCart
            }
            """)
            variables = {}
        
        try:
            # Đảm bảo có session mới
            await self.ensure_session()
            
            result = await self.execute_graphql(graphql_query, variables, method="POST")
            
            if result.get("success", False):
                data = result.get("data", {})
                
                if is_guest:
                    cart_id = data.get("createGuestCart", {}).get("cart", {}).get("id")
                else:
                    cart_id = data.get("cartId")
                
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
            # Đảm bảo có session và event loop hợp lệ
            try:
                # Kiểm tra nếu event loop đã đóng
                if hasattr(self, '_loop') and self._loop is not None and self._loop.is_closed():
                    logger.warning("Event loop đã đóng trong add_to_cart, tạo mới event loop")
                    # Đóng session hiện tại nếu có
                    await self.close()
                    # Tạo mới event loop
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)
                    self._session = None
            except Exception as e:
                logger.warning(f"Lỗi khi kiểm tra event loop trong add_to_cart: {str(e)}")
            
            # Đảm bảo session được khởi tạo sau khi kiểm tra event loop
            await self.ensure_session()
            
            # Sử dụng cart_id từ tham số hoặc từ session
            target_cart_id = cart_id or self._cart_id
            
            # Nếu không có giỏ hàng, tạo mới
            if not target_cart_id:
                try:
                    create_result = await self.create_cart(is_guest=True)
                    if not create_result.get("success", False):
                        return create_result
                    target_cart_id = create_result.get("cart_id")
                    self._cart_id = target_cart_id
                except Exception as cart_error:
                    if "event loop" in str(cart_error).lower():
                        # Xử lý lỗi event loop khi tạo giỏ hàng
                        logger.warning("Lỗi event loop khi tạo giỏ hàng, thử lại sau khi tạo mới event loop")
                        await self.close()
                        if hasattr(self, '_loop') and self._loop and not self._loop.is_closed():
                            self._loop.close()
                        self._loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(self._loop)
                        self._session = None
                        await self.ensure_session()
                        # Thử lại tạo giỏ hàng
                        create_result = await self.create_cart(is_guest=True)
                        if not create_result.get("success", False):
                            return create_result
                        target_cart_id = create_result.get("cart_id")
                        self._cart_id = target_cart_id
                    else:
                        # Các lỗi khác
                        raise
            
            # Thử thêm sản phẩm với số lần thử lại
            for attempt in range(retry_count):
                try:
                    result = await _try_add_to_cart(target_cart_id)
                except Exception as e:
                    if "event loop" in str(e).lower() and attempt < retry_count - 1:
                        # Xử lý lỗi event loop
                        logger.warning(f"Lỗi event loop khi thêm sản phẩm (lần thử {attempt+1}/{retry_count}), tạo lại event loop")
                        await self.close()
                        if hasattr(self, '_loop') and self._loop and not self._loop.is_closed():
                            self._loop.close()
                        self._loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(self._loop)
                        self._session = None
                        await self.ensure_session()
                        continue
                    else:
                        raise
                
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
                        
                        elif error_code == "PRODUCT_NOT_FOUND" and attempt < retry_count - 1:
                            # Thử lại với SKU gốc nếu đang dùng art_no
                            if "use_art_no" in graphql_query:
                                # Tạo query mới không dùng art_no
                                graphql_query = graphql_query.replace("use_art_no: true", "")
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
            
            # Xử lý đặc biệt cho lỗi event loop
            if "event loop" in str(e).lower():
                try:
                    logger.warning("Lỗi event loop phát hiện, thử khôi phục...")
                    await self.close()
                    if hasattr(self, '_loop') and self._loop and not self._loop.is_closed():
                        self._loop.close()
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)
                    self._session = None
                    await self.ensure_session()
                    
                    # Thử lại một lần nữa sau khi khôi phục
                    if retry_count > 0:
                        logger.info("Thử lại thêm sản phẩm vào giỏ hàng sau khi khôi phục event loop...")
                        return await self.add_to_cart(cart_id, product_id, quantity, retry_count - 1)
                except Exception as recovery_error:
                    logger.error(f"Không thể khôi phục sau lỗi event loop: {str(recovery_error)}")
            
            return {
                "success": False,
                "message": f"Error adding product to cart: {str(e)}",
                "code": "ADD_TO_CART_ERROR"
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
    
    async def update_cart_item(
        self, 
        cart_id: Optional[str], 
        cart_item_id: str, 
        quantity: int
    ) -> Dict[str, Any]:
        """
        Cập nhật số lượng sản phẩm trong giỏ hàng.
        
        Args:
            cart_id: ID của giỏ hàng.
            cart_item_id: ID của item trong giỏ hàng.
            quantity: Số lượng mới.
            
        Returns:
            Dict[str, Any]: Kết quả cập nhật.
        """
        graphql_query = """
        mutation UpdateCartItems($cartId: String!, $items: [CartItemUpdateInput!]!) {
          updateCartItems(
            input: {
              cart_id: $cartId,
              cart_items: $items
            }
          ) {
            cart {
              itemsV2 {
                items {
                  id
                  product {
                    name
                    sku
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
          }
        }
        """
        
        try:
            target_cart_id = cart_id or self._cart_id
            if not target_cart_id:
                return {
                    "success": False,
                    "message": "Không có giỏ hàng hiện tại",
                    "code": "NO_CART"
                }
                
            variables = {
                "cartId": target_cart_id,
                "items": [
                    {
                        "cart_item_id": cart_item_id,
                        "quantity": quantity
                    }
                ]
            }
            
            result = await self.execute_graphql(graphql_query, variables)
            
            if result.get("success", False):
                data = result.get("data", {})
                update_result = data.get("updateCartItems", {})
                cart = update_result.get("cart", {})
                
                return {
                    "success": True,
                    "message": "Cập nhật giỏ hàng thành công",
                    "data": {
                        "cart": cart
                    }
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật giỏ hàng: {str(e)}")
            return {
                "success": False,
                "message": f"Error updating cart: {str(e)}",
                "code": "UPDATE_CART_ERROR"
            }
    
    async def remove_cart_item(
        self, 
        cart_id: Optional[str], 
        cart_item_id: str
    ) -> Dict[str, Any]:
        """
        Xóa sản phẩm khỏi giỏ hàng.
        
        Args:
            cart_id: ID của giỏ hàng.
            cart_item_id: ID của item trong giỏ hàng.
            
        Returns:
            Dict[str, Any]: Kết quả xóa.
        """
        graphql_query = """
        mutation RemoveItemFromCart($cartId: String!, $cartItemId: String!) {
          removeItemFromCart(
            input: {
              cart_id: $cartId,
              cart_item_id: $cartItemId
            }
          ) {
            cart {
              itemsV2 {
                items {
                  id
                  product {
                    name
                    sku
                  }
                  quantity
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
          }
        }
        """
        
        try:
            target_cart_id = cart_id or self._cart_id
            if not target_cart_id:
                return {
                    "success": False,
                    "message": "Không có giỏ hàng hiện tại",
                    "code": "NO_CART"
                }
                
            variables = {
                "cartId": target_cart_id,
                "cartItemId": cart_item_id
            }
            
            result = await self.execute_graphql(graphql_query, variables)
            
            if result.get("success", False):
                data = result.get("data", {})
                remove_result = data.get("removeItemFromCart", {})
                cart = remove_result.get("cart", {})
                
                return {
                    "success": True,
                    "message": "Xóa sản phẩm khỏi giỏ hàng thành công",
                    "data": {
                        "cart": cart
                    }
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi xóa sản phẩm khỏi giỏ hàng: {str(e)}")
            return {
                "success": False,
                "message": f"Error removing item from cart: {str(e)}",
                "code": "REMOVE_ITEM_ERROR"
            } 