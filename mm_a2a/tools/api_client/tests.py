#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Kiểm thử cho API client
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Thêm thư mục cha vào path để import các module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mm_a2a.tools.api_client import EcommerceAPIClient
from config import Config

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def test_ping():
    """Kiểm tra kết nối với API."""
    logger.info("=== Kiểm tra kết nối API ===")
    client = EcommerceAPIClient(
        base_url=Config.API_BASE_URL,
        timeout=Config.API_TIMEOUT
    )
    
    result = await client.ping()
    logger.info(f"Kết quả ping: {result}")
    return result.get("success", False)

async def test_search_products():
    """Kiểm tra tìm kiếm sản phẩm."""
    logger.info("=== Kiểm tra tìm kiếm sản phẩm ===")
    client = EcommerceAPIClient(
        base_url=Config.API_BASE_URL,
        timeout=Config.API_TIMEOUT
    )
    
    # Tìm kiếm sản phẩm với từ khóa đơn giản
    result = await client.search_products("ghế", page_size=5)
    success = result.get("success", False)
    if success:
        products = result.get("data", {}).get("products", {})
        total = products.get("total_count", 0)
        logger.info(f"Tìm thấy {total} sản phẩm với từ khóa 'ghế'")
    else:
        logger.error(f"Lỗi tìm kiếm: {result.get('message')}")
    
    return success

async def test_search_multiple_products():
    """Kiểm tra tìm kiếm nhiều từ khóa cùng lúc."""
    logger.info("=== Kiểm tra tìm kiếm nhiều từ khóa ===")
    client = EcommerceAPIClient(
        base_url=Config.API_BASE_URL,
        timeout=Config.API_TIMEOUT
    )
    
    # Tìm kiếm với nhiều từ khóa
    result = await client.search_multiple_products(
        keywords=["bàn", "ghế", "tủ"],
        combine_mode="union",
        page_size=5
    )
    success = result.get("success", False)
    if success:
        products = result.get("data", {}).get("products", {})
        total = products.get("total_count", 0)
        logger.info(f"Tìm thấy {total} sản phẩm với từ khóa 'bàn', 'ghế', 'tủ'")
    else:
        logger.error(f"Lỗi tìm kiếm nhiều từ khóa: {result.get('message')}")
    
    return success

async def test_cart_operations():
    """Kiểm tra các thao tác với giỏ hàng."""
    logger.info("=== Kiểm tra thao tác giỏ hàng ===")
    client = EcommerceAPIClient(
        base_url=Config.API_BASE_URL,
        timeout=Config.API_TIMEOUT
    )
    
    # Tạo giỏ hàng
    cart_result = await client.create_cart(is_guest=True)
    success = cart_result.get("success", False)
    if not success:
        logger.error(f"Lỗi tạo giỏ hàng: {cart_result.get('message')}")
        return False
    
    cart_id = cart_result.get("cart_id")
    logger.info(f"Đã tạo giỏ hàng với ID: {cart_id}")
    
    # Tìm một sản phẩm để thêm vào giỏ hàng
    search_result = await client.search_products("ghế", page_size=1)
    if not search_result.get("success", False):
        logger.error("Không tìm thấy sản phẩm để thêm vào giỏ hàng")
        return False
    
    products = search_result.get("data", {}).get("products", {}).get("items", [])
    if not products:
        logger.error("Không có sản phẩm nào để thêm vào giỏ hàng")
        return False
    
    product_id = products[0].get("sku")
    logger.info(f"Thêm sản phẩm có SKU: {product_id} vào giỏ hàng")
    
    # Thêm sản phẩm vào giỏ hàng
    add_result = await client.add_to_cart(cart_id, product_id, quantity=1)
    if not add_result.get("success", False):
        logger.error(f"Lỗi thêm sản phẩm vào giỏ hàng: {add_result.get('message')}")
        return False
    
    logger.info("Đã thêm sản phẩm vào giỏ hàng thành công")
    
    # Lấy thông tin giỏ hàng
    cart_info = await client.get_cart_info(cart_id)
    if not cart_info.get("success", False):
        logger.error(f"Lỗi lấy thông tin giỏ hàng: {cart_info.get('message')}")
        return False
    
    cart = cart_info.get("data", {}).get("cart", {})
    items = cart.get("itemsV2", {}).get("items", [])
    total_quantity = cart.get("itemsV2", {}).get("total_quantity", 0)
    
    logger.info(f"Giỏ hàng hiện có {total_quantity} sản phẩm")
    
    return True

async def run_tests():
    """Chạy tất cả các kiểm thử."""
    logger.info(f"Bắt đầu kiểm thử lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        test_ping(),
        test_search_products(),
        test_search_multiple_products(),
        test_cart_operations()
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    # Kiểm tra kết quả
    success_count = sum(1 for r in results if r is True)
    error_count = sum(1 for r in results if isinstance(r, Exception))
    failed_count = len(tests) - success_count - error_count
    
    logger.info(f"Kết thúc kiểm thử lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Kết quả: {success_count} thành công, {failed_count} thất bại, {error_count} lỗi")
    
    # Log các lỗi chi tiết
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Kiểm thử {i+1} gặp lỗi: {str(result)}")

if __name__ == "__main__":
    asyncio.run(run_tests()) 