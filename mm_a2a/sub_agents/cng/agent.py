#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sub Agents cho nghiệp vụ C&G (Click and Get) của MM A2A Ecommerce Chatbot
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional

from google.adk.agents import Agent, ParallelAgent, SequentialAgent, LoopAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools.agent_tool import AgentTool

from mm_a2a import prompt
from mm_a2a.tools.memory import memorize, get_memory, memorize_list
from mm_a2a.tools.api_client import EcommerceAPIClient
from mm_a2a.tools.transit import order_status_check, payment_status_check, delivery_status_check, order_coordination
from config import Config

logger = logging.getLogger(__name__)

# Khởi tạo API client
api_client = None

# Khai báo biến toàn cục để theo dõi sự reset API client
_last_search_id = 0

# Thêm biến ID cho product detail
_last_product_id = 0

def get_api_client():
    """Trả về instance API client hiện tại hoặc tạo mới nếu chưa có."""
    global api_client
    if api_client is None:
        # Đảm bảo có event loop hợp lệ trước khi tạo client
        loop = ensure_event_loop()
        api_client = EcommerceAPIClient(
            base_url=Config.API_BASE_URL,
            timeout=Config.API_TIMEOUT,
            loop=loop
        )
    return api_client

# Các công cụ API cho sản phẩm và giỏ hàng
async def search_products(query: str, page_size: int = 10, current_page: int = 1):
    """Tìm kiếm sản phẩm thông qua API."""
    global api_client, _last_search_id
    
    # Tăng ID tìm kiếm để theo dõi các lần tìm kiếm khác nhau
    _last_search_id += 1
    current_search_id = _last_search_id
    
    # Reset API client sau mỗi lần tìm kiếm để tránh lỗi event loop
    api_client = None
    
    try:
        # Tạo mới event loop cho mỗi lần tìm kiếm
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Lấy client mới với event loop mới
        client = get_api_client()
        result = await client.search_products(query, page_size, current_page)
        
        # Nếu tìm kiếm này vẫn là tìm kiếm mới nhất (không bị ghi đè bởi tìm kiếm khác)
        if current_search_id == _last_search_id:
            return result
        else:
            # Nếu đã có tìm kiếm mới hơn, bỏ qua kết quả này
            logger.warning(f"Bỏ qua kết quả tìm kiếm cũ (ID: {current_search_id})")
            return {
                "success": False,
                "message": "Search superseded by newer search",
                "code": "SEARCH_SUPERSEDED"
            }
    except Exception as e:
        logger.error(f"Lỗi khi tìm kiếm sản phẩm: {str(e)}")
        if "event loop" in str(e).lower():
            try:
                # Tạo mới hoàn toàn loop và client
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Reset API client
                api_client = None
                client = get_api_client()
                
                # Thử lại với API client mới
                result = await client.search_products(query, page_size, current_page)
                
                # Nếu tìm kiếm này vẫn là tìm kiếm mới nhất
                if current_search_id == _last_search_id:
                    return result
                else:
                    # Nếu đã có tìm kiếm mới hơn, bỏ qua kết quả này
                    logger.warning(f"Bỏ qua kết quả tìm kiếm cũ sau khi thử lại (ID: {current_search_id})")
                    return {
                        "success": False,
                        "message": "Search superseded by newer search",
                        "code": "SEARCH_SUPERSEDED"
                    }
            except Exception as retry_error:
                logger.error(f"Lỗi khi thử lại tìm kiếm sản phẩm: {str(retry_error)}")
                return {
                    "success": False,
                    "message": f"Lỗi khi tìm kiếm sản phẩm: {str(retry_error)}",
                    "code": "SEARCH_ERROR"
                }
        return {
            "success": False,
            "message": f"Lỗi khi tìm kiếm sản phẩm: {str(e)}",
            "code": "SEARCH_ERROR"
        }

async def get_product_detail(product_id: str):
    """Lấy thông tin chi tiết sản phẩm."""
    global api_client, _last_product_id
    
    # Tăng ID truy vấn để theo dõi các lần truy vấn khác nhau
    _last_product_id += 1
    current_product_query_id = _last_product_id
    
    # Reset API client sau mỗi lần truy vấn để tránh lỗi event loop
    api_client = None
    
    try:
        # Tạo mới event loop cho mỗi lần truy vấn
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Lấy client mới với event loop mới
        client = get_api_client()
        
        # Xác định loại ID và thực hiện truy vấn
        if "_" in product_id:
            # Nếu có dấu "_", giả định là SKU
            result = await client.get_product_by_sku(product_id)
        else:
            # Nếu không, giả định là Article Number
            result = await client.get_product_by_art_no(product_id)
        
        # Nếu truy vấn này vẫn là truy vấn mới nhất (không bị ghi đè bởi truy vấn khác)
        if current_product_query_id == _last_product_id:
            return result
        else:
            # Nếu đã có truy vấn mới hơn, bỏ qua kết quả này
            logger.warning(f"Bỏ qua kết quả truy vấn sản phẩm cũ (ID: {current_product_query_id})")
            return {
                "success": False,
                "message": "Product query superseded by newer query",
                "code": "QUERY_SUPERSEDED"
            }
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin sản phẩm: {str(e)}")
        if "event loop" in str(e).lower():
            try:
                # Tạo mới hoàn toàn loop và client
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Reset API client
                api_client = None
                client = get_api_client()
                
                # Thử lại với API client mới
                if "_" in product_id:
                    result = await client.get_product_by_sku(product_id)
                else:
                    result = await client.get_product_by_art_no(product_id)
                
                # Nếu truy vấn này vẫn là truy vấn mới nhất
                if current_product_query_id == _last_product_id:
                    return result
                else:
                    # Nếu đã có truy vấn mới hơn, bỏ qua kết quả này
                    logger.warning(f"Bỏ qua kết quả truy vấn sản phẩm cũ sau khi thử lại (ID: {current_product_query_id})")
                    return {
                        "success": False,
                        "message": "Product query superseded by newer query",
                        "code": "QUERY_SUPERSEDED"
                    }
            except Exception as retry_error:
                logger.error(f"Lỗi khi thử lại lấy thông tin sản phẩm: {str(retry_error)}")
                return {
                    "success": False,
                    "message": f"Lỗi khi lấy thông tin sản phẩm: {str(retry_error)}",
                    "code": "PRODUCT_DETAIL_ERROR"
                }
        return {
            "success": False,
            "message": f"Lỗi khi lấy thông tin sản phẩm: {str(e)}",
            "code": "PRODUCT_DETAIL_ERROR"
        }

async def add_to_cart(cart_id: str, product_id: str, quantity: int = 1):
    """Thêm sản phẩm vào giỏ hàng."""
    global api_client
    try:
        # Đảm bảo event loop hợp lệ
        ensure_event_loop()
        client = get_api_client()
        return await client.add_to_cart(cart_id, product_id, quantity)
    except Exception as e:
        logger.error(f"Lỗi khi thêm sản phẩm vào giỏ hàng: {str(e)}")
        if "event loop" in str(e).lower():
            # Khởi tạo lại API client với event loop mới
            api_client = None
            # Tạo mới event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            client = get_api_client()
            # Thử lại với API client mới
            return await client.add_to_cart(cart_id, product_id, quantity)
        return {
            "success": False,
            "message": f"Lỗi khi thêm sản phẩm vào giỏ hàng: {str(e)}",
            "code": "ADD_TO_CART_ERROR"
        }

async def create_cart(is_guest: bool = False):
    """Tạo giỏ hàng mới."""
    global api_client
    try:
        # Đảm bảo event loop hợp lệ
        ensure_event_loop()
        client = get_api_client()
        result = await client.create_cart(is_guest)
        if result.get("success", False) and result.get("cart_id"):
            # Lưu cart_id vào bộ nhớ phiên để các agent khác có thể sử dụng
            await memorize(key="cart_id", value=result.get("cart_id"))
        return result
    except Exception as e:
        logger.error(f"Lỗi khi tạo giỏ hàng: {str(e)}")
        if "event loop" in str(e).lower():
            # Khởi tạo lại API client với event loop mới
            api_client = None
            # Tạo mới event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            client = get_api_client()
            # Thử lại với API client mới
            return await client.create_cart(is_guest)
        return {
            "success": False,
            "message": f"Lỗi khi tạo giỏ hàng: {str(e)}",
            "code": "CREATE_CART_ERROR"
        }

def ensure_event_loop():
    """Kiểm tra và đảm bảo event loop hợp lệ."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_closed():
            logger.warning("Event loop đã đóng, tạo mới event loop")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop
        return loop
    except RuntimeError:
        # Không có event loop đang chạy
        logger.info("Không có event loop đang chạy, tạo mới event loop")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra event loop: {str(e)}")
        # Tạo mới event loop trong trường hợp có lỗi
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

async def login(email: str, password: str):
    """Đăng nhập vào hệ thống."""
    try:
        ensure_event_loop()
        client = get_api_client()
        return await client.login(email, password)
    except Exception as e:
        logger.error(f"Lỗi khi đăng nhập: {str(e)}")
        if "event loop" in str(e).lower():
            global api_client
            api_client = None
            client = get_api_client()
            return await client.login(email, password)
        return {
            "success": False, 
            "message": f"Lỗi khi đăng nhập: {str(e)}",
            "code": "LOGIN_ERROR"
        }

async def login_with_mcard(hash_value: str, store: str, cust_no: str, phone: str, cust_no_mm: str, cust_name: str):
    """Đăng nhập bằng thông tin MCard."""
    try:
        ensure_event_loop()
        client = get_api_client()
        return await client.login_with_mcard(hash_value, store, cust_no, phone, cust_no_mm, cust_name)
    except Exception as e:
        logger.error(f"Lỗi khi đăng nhập bằng MCard: {str(e)}")
        if "event loop" in str(e).lower():
            global api_client
            api_client = None
            client = get_api_client()
            return await client.login_with_mcard(hash_value, store, cust_no, phone, cust_no_mm, cust_name)
        return {
            "success": False,
            "message": f"Lỗi khi đăng nhập bằng MCard: {str(e)}",
            "code": "MCARD_LOGIN_ERROR"
        }

# Custom agent để kiểm tra kết quả và quyết định dừng vòng lặp
class CartResultChecker(Agent):
    """Agent kiểm tra kết quả thao tác giỏ hàng và quyết định dừng vòng lặp nếu thành công."""
    name: str = "cart_result_checker"
    description: str = "Kiểm tra kết quả thao tác giỏ hàng và quyết định dừng vòng lặp nếu thành công"
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # Kiểm tra kết quả từ memory
        cart_result = ctx.session.state.get("cart_operation_result", {})
        success = cart_result.get("success", False)
        
        # Tạo phản hồi dựa trên kết quả
        message = "Đã kiểm tra kết quả thao tác giỏ hàng."
        if success:
            message = "Thao tác giỏ hàng thành công!"
        else:
            message = f"Thao tác giỏ hàng thất bại: {cart_result.get('message', 'Không rõ lỗi')}"
        
        # Trả về sự kiện với hành động dừng vòng lặp nếu thành công
        yield Event(
            author=self.name,
            content=message,
            actions=EventActions(escalate=success)  # Dừng vòng lặp nếu thành công
        )

cart_result_checker = CartResultChecker()

# Khởi tạo Sub-agents cho sản phẩm và giỏ hàng
class CartManagerAgent(Agent):
    name: str = "cart_manager_agent"
    description: str = "Quản lý giỏ hàng và quy trình thanh toán"
    
cart_manager_agent = Agent(
    model="gemini-2.0-flash-001",
    name="cart_manager_agent",
    description="Quản lý giỏ hàng và quy trình thanh toán",
    instruction=prompt.CART_MANAGER_INSTR,
    tools=[
        add_to_cart,
        create_cart,
        memorize,
        get_memory
    ],
)

# Tạo LoopAgent để thử lại thao tác giỏ hàng nếu thất bại
class CartRetryAgent(LoopAgent):
    name: str = "cart_retry_agent"
    description: str = "Thử lại thao tác giỏ hàng nếu thất bại"
    
cart_retry_agent = LoopAgent(
    name="cart_retry_agent",
    description="Thử lại thao tác giỏ hàng nếu thất bại",
    max_iterations=3,  # Thử tối đa 3 lần
    sub_agents=[
        cart_manager_agent,
        cart_result_checker
    ]
)

class ProductAgent(Agent):
    name: str = "product_agent"
    description: str = "Tìm kiếm và hiển thị thông tin sản phẩm"

product_agent = Agent(
    model="gemini-2.0-flash-001",
    name="product_agent",
    description="Tìm kiếm và hiển thị thông tin sản phẩm",
    instruction=prompt.PRODUCT_AGENT_INSTR,
    tools=[
        search_products,
        get_product_detail,
        memorize_list,
        get_memory
    ],
)

# Tạo các Agent con xử lý đơn hàng
class OrderDetailsAgent(Agent):
    name: str = "order_details_agent"
    description: str = "Kiểm tra thông tin chi tiết đơn hàng"
    output_key: str = "order_details"

order_details_agent = Agent(
    model="gemini-2.0-flash-001",
    name="order_details_agent",
    description="Kiểm tra thông tin chi tiết đơn hàng",
    instruction=prompt.ORDER_AGENT_INSTR,
    tools=[order_status_check, get_memory],
    output_key="order_details"
)

class PaymentDetailsAgent(Agent):
    name: str = "payment_details_agent"
    description: str = "Kiểm tra thông tin thanh toán đơn hàng"
    output_key: str = "payment_details"

payment_details_agent = Agent(
    model="gemini-2.0-flash-001",
    name="payment_details_agent",
    description="Kiểm tra thông tin thanh toán đơn hàng",
    instruction=prompt.ORDER_AGENT_INSTR,
    tools=[payment_status_check, get_memory],
    output_key="payment_details"
)

class DeliveryDetailsAgent(Agent):
    name: str = "delivery_details_agent"
    description: str = "Kiểm tra thông tin giao hàng"
    output_key: str = "delivery_details"

delivery_details_agent = Agent(
    model="gemini-2.0-flash-001",
    name="delivery_details_agent",
    description="Kiểm tra thông tin giao hàng",
    instruction=prompt.ORDER_AGENT_INSTR,
    tools=[delivery_status_check, get_memory],
    output_key="delivery_details"
)

# Sử dụng ParallelAgent để chạy song song các agent kiểm tra
class ParallelCheckAgent(ParallelAgent):
    name: str = "parallel_check_agent"
    description: str = "Chạy song song các agent kiểm tra thông tin đơn hàng"

parallel_check_agent = ParallelAgent(
    name="parallel_check_agent",
    description="Chạy song song các agent kiểm tra thông tin đơn hàng",
    sub_agents=[
        order_details_agent,
        payment_details_agent,
        delivery_details_agent
    ]
)

# Tạo agent tổng hợp kết quả
class SummaryAgent(Agent):
    name: str = "summary_agent"
    description: str = "Tổng hợp thông tin đơn hàng từ các agent kiểm tra"

summary_agent = Agent(
    model="gemini-2.0-flash-001",
    name="summary_agent",
    description="Tổng hợp thông tin đơn hàng từ các agent kiểm tra",
    instruction="""
    Bạn là một trợ lý tổng hợp thông tin đơn hàng. Nhiệm vụ của bạn là kết hợp thông tin từ ba nguồn:
    1. Thông tin chi tiết đơn hàng (order_details)
    2. Thông tin thanh toán (payment_details) 
    3. Thông tin giao hàng (delivery_details)
    
    Hãy tạo một bản tóm tắt đầy đủ về đơn hàng của khách hàng bao gồm tất cả các thông tin quan trọng.
    Định dạng thông tin theo mẫu ORDER_STATUS_FORMAT, đảm bảo nó dễ đọc và đầy đủ thông tin.
    
    Nhớ lưu trữ thông tin tổng hợp vào bộ nhớ phiên để có thể sử dụng trong tương lai.
    """,
    tools=[memorize, get_memory],
)

# Tạo SequentialAgent để điều phối luồng xử lý đơn hàng
class OrderFlowAgent(SequentialAgent):
    name: str = "order_flow_agent"
    description: str = "Điều phối quá trình kiểm tra và tổng hợp thông tin đơn hàng"

order_flow_agent = SequentialAgent(
    name="order_flow_agent",
    description="Điều phối quá trình kiểm tra và tổng hợp thông tin đơn hàng",
    sub_agents=[
        parallel_check_agent,  # Chạy song song các agent kiểm tra
        summary_agent          # Tổng hợp kết quả
    ]
)

# Khởi tạo CnG Agent chính
class CngAgent(Agent):
    name: str = "cng_agent"
    description: str = "CnG (Click and Get) Agent cho MM A2A Ecommerce Chatbot"

# Đảm bảo event loop được thiết lập trước khi khởi tạo agent
# Tạo đoạn code khởi tạo event loop mạnh mẽ hơn
loop = None
try:
    loop = asyncio.get_running_loop()
    # Nếu loop đã đóng, tạo mới
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
except RuntimeError:
    # Không có event loop đang chạy
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
except Exception as e:
    logger.error(f"Lỗi khi thiết lập event loop: {str(e)}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Lưu loop tạm thời để sử dụng khi cần
_temp_loop = loop

cng_agent = Agent(
    model="gemini-2.0-flash-001",
    name="cng_agent",
    description="CnG (Click and Get) Agent cho MM A2A Ecommerce Chatbot",
    instruction=prompt.CNG_AGENT_INSTR,
    sub_agents=[
        cart_retry_agent,   # Sử dụng agent retry thay vì cart_manager trực tiếp
        product_agent,
        order_flow_agent
    ],
    tools=[
        login,
        login_with_mcard,
        memorize,
        get_memory,
        AgentTool(agent=order_details_agent),  # Cho phép gọi trực tiếp các agent con nếu cần
        AgentTool(agent=payment_details_agent),
        AgentTool(agent=delivery_details_agent)
    ],
)