#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script kiểm tra API client mới
"""

import asyncio
import logging
import sys
import os

# Thêm thư mục gốc vào sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from config import Config
from mm_a2a.tools.api_client import EcommerceAPIClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("test_api_client")

async def test_api_client():
    """Kiểm tra các chức năng cơ bản của API client."""
    
    logger.info("Khởi tạo EcommerceAPIClient")
    client = EcommerceAPIClient(
        base_url=Config.API_BASE_URL,
        timeout=Config.API_TIMEOUT
    )
    
    try:
        # Kiểm tra kết nối
        logger.info("Kiểm tra kết nối đến API")
        ping_result = await client.ping()
        logger.info(f"Kết quả ping: {ping_result}")
        
        # Tìm kiếm sản phẩm
        search_term = "ăn cơm"
        logger.info(f"Tìm kiếm sản phẩm với từ khóa: {search_term}")
        search_result = await client.search_products(search_term, page_size=3)
        
        if search_result.get("success", False):
            products = search_result.get("data", {}).get("products", {}).get("items", [])
            logger.info(f"Tìm thấy {len(products)} sản phẩm")
            for product in products:
                logger.info(f"- {product.get('name')} (SKU: {product.get('sku')})")
        else:
            logger.error(f"Lỗi tìm kiếm sản phẩm: {search_result.get('message')}")
        
        # Tạo giỏ hàng
        logger.info("Tạo giỏ hàng mới")
        cart_result = await client.create_cart(is_guest=True)
        
        if cart_result.get("success", False):
            cart_id = cart_result.get("cart_id")
            logger.info(f"Tạo giỏ hàng thành công, ID: {cart_id}")
            
            # Thêm sản phẩm vào giỏ hàng nếu có sản phẩm
            if products:
                product = products[0]
                sku = product.get("sku")
                logger.info(f"Thêm sản phẩm {product.get('name')} (SKU: {sku}) vào giỏ hàng")
                add_result = await client.add_to_cart(product_id=sku, quantity=1)
                
                if add_result.get("success", False):
                    logger.info("Thêm sản phẩm vào giỏ hàng thành công")
                else:
                    logger.error(f"Lỗi thêm sản phẩm vào giỏ hàng: {add_result.get('message')}")
                
                # Xem thông tin giỏ hàng
                logger.info("Lấy thông tin giỏ hàng")
                cart_info = await client.get_cart_info()
                
                if cart_info.get("success", False):
                    cart_items = cart_info.get("data", {}).get("cart", {}).get("items", [])
                    logger.info(f"Giỏ hàng có {len(cart_items)} sản phẩm")
                else:
                    logger.error(f"Lỗi lấy thông tin giỏ hàng: {cart_info.get('message')}")
        else:
            logger.error(f"Lỗi tạo giỏ hàng: {cart_result.get('message')}")
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra API client: {str(e)}")
    
    finally:
        # Đóng các session
        logger.info("Đóng các session")
        await client.close()
        logger.info("Hoàn thành kiểm tra")

def main():
    """Hàm main chạy test."""
    asyncio.run(test_api_client())

if __name__ == "__main__":
    main() 