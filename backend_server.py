#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MM A2A Ecommerce Chatbot - Backend Server với FastAPI và Uvicorn
Phục vụ API trên port 5000 để frontend có thể giao tiếp
"""

import os
import json
import uuid
import asyncio
import logging
import time
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# Import các module cần thiết từ MM A2A Ecommerce Chatbot
from mm_a2a.agent.agent import root_agent
from config import Config, active_config
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from mm_a2a.tools.memory import _get_session_data, _store_session_data

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("backend_server.log", encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

# Dictionary toàn cục để lưu trữ thông tin người dùng
# Key: "{user_id}:{session_id}", Value: Dict chứa thông tin user_profile
user_profiles = {}

# Tạo app
app = FastAPI(title="MM A2A Ecommerce Chatbot API")

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong môi trường production, nên giới hạn nguồn gốc
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tạo session service để lưu trữ phiên chat
session_service = InMemorySessionService()
APP_NAME = "mm_a2a_ecommerce"

# Khởi tạo runner để chạy agent
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service
)

# Models cho API
class ChatRequest(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    message: str
    message_type: str = "text"
    # Các parameters mới
    include_raw_response: bool = False
    stream: bool = False
    include_session_data: bool = False
    response_format: str = "text"
    include_timestamps: bool = False
    max_tokens: Optional[int] = None
    include_thinking: bool = False
    max_context_messages: int = 20  # Giới hạn số lượng tin nhắn trong context
    user_profile: Optional[Dict[str, Any]] = None  # Thông tin người dùng từ frontend

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str

class SessionData(BaseModel):
    conversation_history: List[ConversationMessage] = []
    memory: Dict[str, Any] = {}
    user_profile: Optional[Dict[str, Any]] = None

def process_model_response(text: str) -> str:
    """
    Xử lý phản hồi từ mô hình để định dạng đúng cách cho frontend.
    
    Nhiều khi mô hình trả về dữ liệu JSON trong phản hồi, nhưng lại được bọc trong
    các dấu backtick (markdown code block). Hàm này giúp làm sạch phản hồi để
    frontend hiển thị đúng.
    """
    if not text:
        return ""
    
    logger.info(f"Xử lý phản hồi từ mô hình: {text[:200]}...")
        
    # Kiểm tra phản hồi có phải là JSON trong code block không
    json_code_block_pattern = r'```(?:json)?\s*(.*?)\s*```'
    json_match = re.search(json_code_block_pattern, text, re.DOTALL)
    
    if json_match:
        # Tìm thấy khối JSON - trích xuất nội dung
        json_content = json_match.group(1).strip()
        try:
            # Thử phân tích nội dung JSON
            json_data = json.loads(json_content)
            
            # Ghi log JSON đã xử lý
            logger.info(f"JSON đã xử lý: {json.dumps(json_data, ensure_ascii=False)[:200]}...")
            
            # Chuẩn hóa định dạng dữ liệu sản phẩm
            # Đảm bảo luôn có trường "products" ở root của JSON
            if 'data' in json_data and 'products' in json_data['data'] and not 'products' in json_data:
                # Chuyển trường products từ data lên level root
                json_data['products'] = json_data['data']['products']
                # Chuyển các trường khác từ data nếu cần
                if 'total_results' in json_data['data']:
                    json_data['total_results'] = json_data['data']['total_results']
                if 'page' in json_data['data']:
                    json_data['page'] = json_data['data']['page']
            
            # Đảm bảo có trường success = true nếu chưa có
            if not 'success' in json_data and 'products' in json_data:
                json_data['success'] = True
                
            # Đảm bảo có trường message nếu chưa có
            if not 'message' in json_data and 'products' in json_data:
                if 'total_results' in json_data:
                    json_data['message'] = f"Đã tìm thấy {json_data['total_results']} sản phẩm"
                else:
                    json_data['message'] = f"Đã tìm thấy {len(json_data['products'])} sản phẩm"
                    
            # Đảm bảo có trường action nếu chưa có
            if not 'action' in json_data and 'products' in json_data:
                json_data['action'] = "search_products"
            
            # Nếu có một đối tượng products trong JSON, đây có thể là kết quả tìm kiếm sản phẩm
            if 'products' in json_data and isinstance(json_data.get('products'), list):
                logger.info(f"Phát hiện dữ liệu JSON chứa sản phẩm: {len(json_data['products'])} sản phẩm")
                
                # Đảm bảo các trường cần thiết trong mỗi sản phẩm
                for product in json_data['products']:
                    # Đảm bảo product_id
                    if 'id' in product and not 'product_id' in product:
                        product['product_id'] = product['id']
                    # Đảm bảo có giá gốc và phần trăm giảm giá
                    if 'price' in product and not 'original_price' in product:
                        product['original_price'] = product['price']
                        product['discount_percentage'] = 0
                    # Đảm bảo có thương hiệu
                    if not 'brand' in product:
                        product['brand'] = "No brand"
            
            # Trả về chuỗi JSON đã làm sạch để frontend có thể phân tích trực tiếp
            return json.dumps(json_data, ensure_ascii=False)
        except json.JSONDecodeError as e:
            # Nếu không phải JSON hợp lệ, ghi log lỗi và giữ nguyên nội dung
            logger.warning(f"Nội dung không phải JSON hợp lệ mặc dù trong code block: {json_content[:100]}... Lỗi: {str(e)}")
            return text
    
    # Thử tìm kiếm trực tiếp đối tượng JSON không trong code block
    try:
        # Kiểm tra xem toàn bộ văn bản có phải là JSON hợp lệ không
        json_data = json.loads(text)
        logger.info("Phát hiện JSON trực tiếp không có code block")
        
        # Chuẩn hóa định dạng dữ liệu sản phẩm
        # Đảm bảo luôn có trường "products" ở root của JSON
        if 'data' in json_data and 'products' in json_data['data'] and not 'products' in json_data:
            # Chuyển trường products từ data lên level root
            json_data['products'] = json_data['data']['products']
            # Chuyển các trường khác từ data nếu cần
            if 'total_results' in json_data['data']:
                json_data['total_results'] = json_data['data']['total_results']
            if 'page' in json_data['data']:
                json_data['page'] = json_data['data']['page']
                
        # Đảm bảo có trường success = true nếu chưa có
        if not 'success' in json_data and 'products' in json_data:
            json_data['success'] = True
        
        # Đảm bảo có trường message nếu chưa có
        if not 'message' in json_data and 'products' in json_data:
            if 'total_results' in json_data:
                json_data['message'] = f"Đã tìm thấy {json_data['total_results']} sản phẩm"
            else:
                json_data['message'] = f"Đã tìm thấy {len(json_data['products'])} sản phẩm"
                
        # Đảm bảo có trường action nếu chưa có
        if not 'action' in json_data and 'products' in json_data:
            json_data['action'] = "search_products"
        
        # Nếu có, trả về chuỗi JSON ban đầu
        if 'products' in json_data and isinstance(json_data.get('products'), list):
            logger.info(f"Phát hiện dữ liệu JSON trực tiếp chứa sản phẩm: {len(json_data['products'])} sản phẩm")
            
            # Đảm bảo các trường cần thiết trong mỗi sản phẩm
            for product in json_data['products']:
                # Đảm bảo product_id
                if 'id' in product and not 'product_id' in product:
                    product['product_id'] = product['id']
                # Đảm bảo có giá gốc và phần trăm giảm giá
                if 'price' in product and not 'original_price' in product:
                    product['original_price'] = product['price']
                    product['discount_percentage'] = 0
                # Đảm bảo có thương hiệu
                if not 'brand' in product:
                    product['brand'] = "No brand"
        
        # Trả về chuỗi JSON gốc để frontend có thể phân tích
        return json.dumps(json_data, ensure_ascii=False)
    except json.JSONDecodeError:
        # Không phải JSON hợp lệ, tiếp tục xử lý
        pass
    
    # Tìm kiếm các mẫu JSON khác trong văn bản
    # Ví dụ: tìm kiếm mẫu "{ ... }" bao quanh toàn bộ đối tượng
    json_pattern = r'\{[\s\S]*\}'
    json_matches = re.findall(json_pattern, text)
    
    for potential_json in json_matches:
        if len(potential_json) > 50:  # Chỉ xét các chuỗi đủ dài là JSON tiềm năng
            try:
                json_data = json.loads(potential_json)
                logger.info(f"Phát hiện JSON tiềm năng trong văn bản: {potential_json[:100]}...")
                
                # Chuẩn hóa định dạng dữ liệu sản phẩm
                # Đảm bảo luôn có trường "products" ở root của JSON
                if 'data' in json_data and 'products' in json_data['data'] and not 'products' in json_data:
                    # Chuyển trường products từ data lên level root
                    json_data['products'] = json_data['data']['products']
                    # Chuyển các trường khác từ data nếu cần
                    if 'total_results' in json_data['data']:
                        json_data['total_results'] = json_data['data']['total_results']
                    if 'page' in json_data['data']:
                        json_data['page'] = json_data['data']['page']
                
                # Nếu có đối tượng products, đây có thể là kết quả tìm kiếm
                if 'products' in json_data and isinstance(json_data.get('products'), list):
                    logger.info(f"Phát hiện dữ liệu JSON nhúng chứa sản phẩm: {len(json_data['products'])} sản phẩm")
                    
                    # Đảm bảo các trường cần thiết trong mỗi sản phẩm
                    for product in json_data['products']:
                        # Đảm bảo product_id
                        if 'id' in product and not 'product_id' in product:
                            product['product_id'] = product['id']
                        # Đảm bảo có giá gốc và phần trăm giảm giá
                        if 'price' in product and not 'original_price' in product:
                            product['original_price'] = product['price']
                            product['discount_percentage'] = 0
                        # Đảm bảo có thương hiệu
                        if not 'brand' in product:
                            product['brand'] = "No brand"
                    
                    # Trả về đối tượng JSON đã trích xuất
                    return json.dumps(json_data, ensure_ascii=False)
                
                # Nếu JSON chứa thông tin quan trọng khác như cart
                if 'cart' in json_data or 'cart_items' in json_data:
                    logger.info("Phát hiện dữ liệu JSON chứa thông tin giỏ hàng")
                    return json.dumps(json_data, ensure_ascii=False)
            except json.JSONDecodeError:
                # Không phải JSON hợp lệ, bỏ qua
                continue
    
    # Nếu không phải JSON hoặc không tìm thấy JSON hợp lệ, trả về nguyên bản
    return text

# Đảm bảo event loop hợp lệ
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

def prepare_model_context(user_profile: Optional[Dict[str, Any]]) -> str:
    """Chuẩn bị context cho model dựa trên thông tin đã biết về người dùng."""
    if not user_profile:
        logger.info("Không có user_profile để chuẩn bị context")
        return ""
        
    logger.info(f"Chuẩn bị context từ user_profile: {user_profile}")
    
    context_parts = []
    
    # Thêm thông tin profile
    profile_info = []
    if isinstance(user_profile, dict):
        # Xử lý nếu user_profile là dict
        if user_profile.get('name'):
            profile_info.append(f"Tên khách hàng: {user_profile['name']}")
        if user_profile.get('phone'):
            profile_info.append(f"SĐT: {user_profile['phone']}")
        if user_profile.get('address'):
            profile_info.append(f"Địa chỉ: {user_profile['address']}")
        if user_profile.get('shopping_preferences'):
            if isinstance(user_profile['shopping_preferences'], list):
                profile_info.append(f"Sở thích mua sắm: {', '.join(user_profile['shopping_preferences'])}")
            else:
                profile_info.append(f"Sở thích mua sắm: {user_profile['shopping_preferences']}")
        
        # Thêm thông tin về lịch sử mua hàng nếu có
        purchase_history = user_profile.get('purchase_history', [])
        if purchase_history and isinstance(purchase_history, list) and len(purchase_history) > 0:
            recent_purchases = purchase_history[-5:]  # 5 mua hàng gần nhất
            purchases_text = []
            for purchase in recent_purchases:
                if isinstance(purchase, dict):
                    product_name = purchase.get('product_name', 'Sản phẩm không tên')
                    date = purchase.get('date', 'không rõ thời gian')
                    purchases_text.append(f"{product_name} (mua ngày {date})")
            
            if purchases_text:
                context_parts.append("Lịch sử mua hàng gần đây:\n" + "\n".join(purchases_text))
            
        # Thêm sản phẩm đã xem gần đây - chi tiết hơn
        viewed_products = user_profile.get('viewed_products', [])
        if viewed_products:
            if isinstance(viewed_products, list):
                recent_products = viewed_products[-5:]  # 5 sản phẩm gần nhất
                viewed_details = []
                for product in recent_products:
                    if isinstance(product, dict):
                        product_name = product.get('name', 'Sản phẩm không tên')
                        product_price = product.get('price', 'không rõ giá')
                        viewed_details.append(f"{product_name} - {product_price}")
                    elif isinstance(product, str):
                        viewed_details.append(product)
                
                if viewed_details:
                    context_parts.append("Sản phẩm đã xem gần đây:\n" + "\n".join(viewed_details))
            else:
                logger.warning(f"viewed_products không phải là list: {viewed_products}")
        
        # Thêm thông tin chi tiết giỏ hàng
        cart_items = user_profile.get('cart_items', [])
        if cart_items:
            if isinstance(cart_items, list):
                cart_info = []
                total_price = 0
                for item in cart_items:
                    if isinstance(item, dict):
                        product_name = item.get('name', 'Sản phẩm không tên')
                        quantity = item.get('quantity', 1)
                        price = item.get('price', 0)
                        item_total = quantity * price
                        total_price += item_total
                        cart_info.append(f"{product_name} - {quantity} cái x {price:,}đ = {item_total:,}đ")
                    else:
                        logger.warning(f"cart_item không phải là dict: {item}")
                
                if cart_info:
                    context_parts.append(f"Giỏ hàng hiện tại (tổng: {total_price:,}đ):\n" + "\n".join(cart_info))
            else:
                logger.warning(f"cart_items không phải là list: {cart_items}")
                
        # Thêm lịch sử tương tác gần đây nếu có
        recent_interactions = user_profile.get('recent_interactions', [])
        if recent_interactions and isinstance(recent_interactions, list) and len(recent_interactions) > 0:
            interaction_summary = []
            for interaction in recent_interactions[-3:]:  # 3 tương tác gần nhất
                if isinstance(interaction, dict):
                    query = interaction.get('query', 'Không rõ câu hỏi')
                    time = interaction.get('time', 'không rõ thời gian')
                    interaction_summary.append(f"- {query} ({time})")
            
            if interaction_summary:
                context_parts.append("Tương tác gần đây:\n" + "\n".join(interaction_summary))
                
        # Thêm thông tin đơn hàng đang theo dõi nếu có
        tracked_orders = user_profile.get('tracked_orders', [])
        if tracked_orders and isinstance(tracked_orders, list) and len(tracked_orders) > 0:
            order_summary = []
            for order in tracked_orders:
                if isinstance(order, dict):
                    order_id = order.get('order_id', 'Không rõ ID')
                    status = order.get('status', 'Không rõ trạng thái')
                    date = order.get('date', 'không rõ thời gian')
                    order_summary.append(f"Đơn hàng #{order_id}: {status} (đặt ngày {date})")
            
            if order_summary:
                context_parts.append("Đơn hàng đang theo dõi:\n" + "\n".join(order_summary))
    else:
        logger.warning(f"user_profile không phải là dict: {type(user_profile)}")
    
    if profile_info:
        context_parts.append("Thông tin khách hàng:\n" + "\n".join(profile_info))
    
    # Tạo system message với context
    if context_parts:
        system_info = "Hãy sử dụng thông tin sau về khách hàng để phục vụ tốt hơn:\n\n" + "\n\n".join(context_parts)
        logger.info(f"Đã tạo context cho model với {len(context_parts)} phần")
    else:
        system_info = "Chưa có thông tin cụ thể về khách hàng này."
        logger.info("Không có thông tin chi tiết về khách hàng")
    
    return system_info

def get_user_profile(user_id: str, session_id: str) -> Dict[str, Any]:
    """Helper function để lấy user_profile từ dictionary toàn cục."""
    profile_key = f"{user_id}:{session_id}"
    profile = user_profiles.get(profile_key, {})
    
    if not profile:
        logger.info(f"Không tìm thấy profile cho {profile_key}")
    else:
        logger.info(f"Đã tìm thấy profile cho {profile_key}: {profile}")
        
    return profile

def manage_context_size(session, max_messages: int = 20):
    """Quản lý kích thước context, giới hạn số lượng tin nhắn."""
    if hasattr(session, 'history') and session.history:
        # Mỗi lượt trao đổi gồm 2 tin nhắn (user và assistant)
        max_history_items = max_messages * 2
        
        if len(session.history) > max_history_items:
            # Giữ lại tin nhắn đầu tiên (lời chào) và các tin nhắn mới nhất
            session.history = [session.history[0]] + session.history[-(max_history_items-1):]
            logger.info(f"Đã cắt bớt context, giữ lại {len(session.history)} tin nhắn")

@app.get("/")
async def root():
    return {"message": "MM A2A Ecommerce Chatbot API đang hoạt động"}

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "MM A2A Ecommerce Chatbot API"}

@app.post("/api/auth-llm")
@app.get("/api/auth-llm")
async def auth_llm(request: Request):
    """Endpoint giả lập xác thực LLM để tránh lỗi 404 từ frontend."""
    try:
        # Tạo token giả
        token = str(int(time.time() * 1000))  # Unix timestamp milliseconds
        
        # Log request
        logger.info(f"Nhận yêu cầu xác thực LLM từ method: {request.method}")
        
        # Trả về token giả
        return {
            "success": True,
            "message": "Xác thực thành công",
            "data": {
                "token": token,
                "expires_in": 3600  # 1 giờ
            }
        }
    except Exception as e:
        logger.error(f"Lỗi xác thực LLM: {str(e)}")
        logger.exception(e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": f"Lỗi xác thực: {str(e)}",
                "error_code": "AUTH_ERROR",
                "error_details": {
                    "stack_trace": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        # Kiểm tra nếu yêu cầu stream thì chuyển hướng đến endpoint stream
        if request.stream:
            return await stream_chat(request)
            
        # Tạo hoặc lấy user_id và session_id
        user_id = request.user_id or str(uuid.uuid4())
        session_id = request.session_id or str(uuid.uuid4())
        
        # Tạo key cho dictionary toàn cục
        profile_key = f"{user_id}:{session_id}"
        
        # Tạo session nếu chưa có
        try:
            session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
            logger.info(f"Đã tạo session mới cho {profile_key}")
        except Exception as e:
            # Session có thể đã tồn tại, bỏ qua lỗi
            logger.warning(f"Không thể tạo session mới (có thể đã tồn tại): {e}")
            pass
        
        # Lấy session hiện tại
        session = session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
        
        # Load memory from previous session
        try:
            saved_memory = _get_session_data(session_id)
            if saved_memory:
                session.state.update(saved_memory)
                logger.info(f"Loaded {len(saved_memory)} memory entries for {profile_key}")
        except Exception as e:
            logger.warning(f"Error loading session memory for {profile_key}: {e}")
        
        # Cập nhật thông tin user_profile từ request (từ frontend)
        user_profile = request.user_profile
        if user_profile:
            # Cập nhật thông tin từ request vào dictionary toàn cục
            user_profiles[profile_key] = user_profile
            logger.info(f"Đã cập nhật profile từ request cho {profile_key}")
        
        # Quản lý kích thước context
        manage_context_size(session, request.max_context_messages)
        
        # Lấy user_profile hiện tại từ dictionary toàn cục
        current_profile = get_user_profile(user_id, session_id)
        
        # Chuẩn bị context cho model từ user_profile
        model_context = ""
        if current_profile:
            model_context = prepare_model_context(current_profile)
        
        # Inject memory context vào system prompt
        memory_items = {k: v for k, v in session.state.items() if not str(k).startswith("_")}
        if memory_items:
            mem_text = "Những thông tin đã lưu:\n" + "\n".join(f"{k}: {v}" for k, v in memory_items.items())
            model_context = mem_text + "\n\n" + model_context
        
        # Tạo nội dung người dùng
        user_content = types.Content(role='user', parts=[types.Part(text=request.message)])
        
        # Thêm system message với context nếu có
        if model_context:
            try:
                # Thử thêm system prompt với context
                system_content = types.Content(role='system', parts=[types.Part(text=model_context)])
                runner.update_system_instruction(user_id=user_id, session_id=session_id, content=system_content)
                logger.info("Đã cập nhật system prompt với context")
            except Exception as e:
                logger.warning(f"Không thể cập nhật system prompt: {e}")
        
        # Biến để lưu phản hồi cuối cùng
        final_response = None
        raw_response = None
        timestamp = datetime.now().isoformat()
        
        # Lưu trữ quá trình suy nghĩ nếu được yêu cầu
        thinking_process = None
        
        # Đảm bảo event loop hợp lệ
        ensure_event_loop()
        
        # Chạy agent thông qua runner để xử lý tin nhắn
        for event in runner.run(user_id=user_id, session_id=session_id, new_message=user_content):
            if event.is_final_response() and event.content and event.content.parts:
                part_text = None
                if len(event.content.parts) > 0 and hasattr(event.content.parts[0], 'text'):
                    part_text = event.content.parts[0].text
                
                if part_text is not None:
                    final_response = part_text
                    
                if request.include_raw_response or request.response_format == "raw":
                    try:
                        if hasattr(event.content, 'to_dict'):
                            raw_response = {
                                "model_output": event.content.to_dict(),
                                "tokens_used": getattr(event, "tokens_used", 0),
                                "model_name": "gemini-2.0-flash-001"
                            }
                        else:
                            # Nếu không có phương thức to_dict, tạo một đối tượng thay thế
                            raw_response = {
                                "model_output": {"text": final_response},
                                "tokens_used": getattr(event, "tokens_used", 0),
                                "model_name": "gemini-2.0-flash-001"
                            }
                    except Exception as e:
                        logger.error(f"Lỗi khi tạo raw_response: {str(e)}")
                        logger.exception(e)
                        # Vẫn tạo raw_response nhưng với thông tin lỗi
                        raw_response = {
                            "error": str(e),
                            "model_output": {"text": final_response},
                            "tokens_used": getattr(event, "tokens_used", 0),
                            "model_name": "gemini-2.0-flash-001"
                        }
            
            # Nếu bật include_thinking, thu thập các suy nghĩ trung gian
            if request.include_thinking and hasattr(event, 'thinking'):
                thinking_process = getattr(event, 'thinking', None)
        
        # Kiểm tra phản hồi
        if final_response is None:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False, 
                    "message": "Không nhận được phản hồi từ chatbot",
                    "error_code": "MODEL_ERROR"
                }
            )
        
        # Xử lý kết quả và ưu tiên suy nghĩ từ chatbot
        processed_response = final_response
        thinking_process = None
        
        # Trích xuất thinking_process từ phản hồi JSON nếu có
        if final_response:
            try:
                # Thử phân tích JSON từ phản hồi
                response_json = json.loads(final_response)
                
                # Nếu có trường thinking_process trong JSON, trích xuất
                if 'thinking_process' in response_json:
                    thinking_process = response_json.get('thinking_process')
                    logger.info(f"Đã trích xuất thinking_process từ phản hồi JSON")
                    
                    # Nếu include_thinking là False, không hiển thị thinking_process trong phản hồi
                    if not request.include_thinking:
                        # Xóa thinking_process khỏi JSON phản hồi
                        response_json.pop('thinking_process', None)
                        # Cập nhật phản hồi
                        processed_response = json.dumps(response_json, ensure_ascii=False)
                        logger.info("Đã loại bỏ thinking_process khỏi phản hồi cuối cùng")
            except json.JSONDecodeError:
                # Không phải JSON, kiểm tra xem có chứa thinking_process không
                # Tìm kiếm mẫu trong text
                thinking_pattern = r'Quá trình tư duy:|thinking_process:|Suy nghĩ của tôi:|THINKING PROCESS:'
                thinking_match = re.search(thinking_pattern, final_response, re.IGNORECASE)
                
                if thinking_match:
                    # Cắt phần văn bản từ vị trí tìm thấy mẫu
                    thinking_index = thinking_match.start()
                    # Tìm dấu hiệu kết thúc (ví dụ: một dòng trống kép)
                    end_patterns = ['\n\n', '\r\n\r\n']
                    end_index = len(final_response)
                    
                    for pattern in end_patterns:
                        pos = final_response[thinking_index:].find(pattern)
                        if pos > 0:
                            end_index = thinking_index + pos
                            break
                    
                    # Trích xuất phần thinking process
                    thinking_process = final_response[thinking_index:end_index].strip()
                    
                    # Loại bỏ phần thinking khỏi phản hồi nếu không cần hiển thị
                    if not request.include_thinking:
                        processed_response = final_response[:thinking_index].strip() + final_response[end_index:].strip()
                        logger.info("Đã loại bỏ thinking_process khỏi phản hồi văn bản")
            
        # Nếu người dùng yêu cầu include_thinking, đảm bảo thinking_process được thêm vào
        if request.include_thinking and thinking_process:
            try:
                # Thử chuyển processed_response thành JSON
                response_data = json.loads(processed_response)
                response_data['thinking_process'] = thinking_process
                processed_response = json.dumps(response_data, ensure_ascii=False)
            except json.JSONDecodeError:
                # Nếu processed_response không phải JSON, thêm thinking_process vào đầu
                processed_response = f"Quá trình tư duy:\n{thinking_process}\n\n{processed_response}"
        
        # Save memory after conversation
        try:
            mem_to_save = {k: v for k, v in session.state.items() if not str(k).startswith("_")}
            _store_session_data(session_id, mem_to_save)
            logger.info(f"Saved {len(mem_to_save)} memory entries for {profile_key}")
        except Exception as e:
            logger.error(f"Error saving session memory for {profile_key}: {e}")
        
        logger.info(f"Trả về LLM response trực tiếp: {processed_response[:100]}...")
            
        # Chuẩn bị dữ liệu phản hồi
        response_data = {
            "response": processed_response,
            "user_id": user_id,
            "session_id": session_id
        }
        
        # Bổ sung dữ liệu theo các tham số yêu cầu
        if (request.include_raw_response or request.response_format == "raw") and raw_response:
            response_data["raw_response"] = raw_response
            
        if request.include_timestamps:
            response_data["timestamp"] = timestamp
            
        if request.include_thinking and thinking_process:
            response_data["thinking"] = thinking_process
            
        if request.include_session_data:
            # Tạo lịch sử hội thoại
            conversation_history = []
            if hasattr(session, 'history') and session.history:
                for msg in session.history:
                    conversation_history.append({
                        "role": msg.role,
                        "content": msg.parts[0].text if msg.parts else "",
                        "timestamp": datetime.now().isoformat()  # Giả định vì không có timestamp thực tế
                    })
            
            # Lấy user_profile từ dictionary toàn cục
            current_profile = get_user_profile(user_id, session_id)
                
            response_data["session_data"] = {
                "conversation_history": conversation_history,
                "memory": getattr(session, 'state', {}),
                "user_profile": current_profile
            }
        
        # Trả về phản hồi thành công
        return {
            "success": True,
            "message": "Xử lý thành công",
            "data": response_data
        }
        
    except Exception as e:
        logger.error(f"Lỗi xử lý chat: {str(e)}")
        logger.exception(e)  # Log full traceback
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False, 
                "message": f"Lỗi xử lý: {str(e)}",
                "error_code": "SERVER_ERROR",
                "error_details": {
                    "stack_trace": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

@app.post("/api/chat/stream")
async def stream_chat(request: ChatRequest):
    """Endpoint để stream phản hồi từ chatbot - trả về trực tiếp phản hồi từ LLM"""
    
    async def event_generator():
        try:
            # Tạo hoặc lấy user_id và session_id
            user_id = request.user_id or str(uuid.uuid4())
            session_id = request.session_id or str(uuid.uuid4())
            
            # Gửi sự kiện bắt đầu
            start_data = {
                "content": "",
                "done": False,
                "started": True
            }
            yield f"data: {json.dumps(start_data)}\n\n"
            
            # Xử lý tất cả yêu cầu thông qua LLM
            try:
                # Tạo session nếu chưa có
                try:
                    session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
                except Exception:
                    # Session có thể đã tồn tại, bỏ qua lỗi
                    pass
                
                # Lấy session hiện tại
                session = session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
                
                # Lấy user_profile hiện tại từ dictionary toàn cục
                profile_key = f"{user_id}:{session_id}"
                current_profile = get_user_profile(user_id, session_id)
                
                # Chuẩn bị context cho model từ user_profile
                model_context = ""
                if current_profile:
                    model_context = prepare_model_context(current_profile)
                
                # Inject memory context vào system prompt để LLM có thể nhớ thông tin phiên trước
                memory_items = {k: v for k, v in session.state.items() if not str(k).startswith("_")}
                if memory_items:
                    mem_text = "Những thông tin đã lưu:\n" + "\n".join(f"{k}: {v}" for k, v in memory_items.items())
                    model_context = mem_text + "\n\n" + model_context
                
                # Cập nhật thông tin user_profile từ request (từ frontend)
                user_profile = request.user_profile
                if user_profile:
                    # Cập nhật thông tin từ request vào dictionary toàn cục
                    user_profiles[profile_key] = user_profile
                
                # Tạo nội dung người dùng
                user_content = types.Content(role='user', parts=[types.Part(text=request.message)])
                
                # Thêm system message với context nếu có
                if model_context:
                    try:
                        # Thử thêm system prompt với context
                        system_content = types.Content(role='system', parts=[types.Part(text=model_context)])
                        runner.update_system_instruction(user_id=user_id, session_id=session_id, content=system_content)
                    except Exception:
                        # Bỏ qua lỗi nếu không thể thêm system prompt
                        pass
                
                # Chạy agent
                accumulated_response = ""
                tokens_used = 0
                
                for event in runner.run(user_id=user_id, session_id=session_id, new_message=user_content):
                    # Kiểm tra event có valid không
                    if (not event or not hasattr(event, 'content') or not event.content or 
                        not hasattr(event.content, 'parts') or not event.content.parts):
                        continue
                    
                    # Lấy text từ parts
                    part_text = None
                    if len(event.content.parts) > 0:
                        if hasattr(event.content.parts[0], 'text'):
                            part_text = event.content.parts[0].text
                    
                    # Nếu part_text là None, bỏ qua
                    if part_text is None:
                        continue
                    
                    # Xử lý phần mới
                    new_text = part_text
                    if accumulated_response:
                        if part_text.startswith(accumulated_response):
                            new_text = part_text[len(accumulated_response):]
                        else:
                            # Nếu không phải tiếp nối, sử dụng toàn bộ
                            new_text = part_text
                    
                    accumulated_response = part_text
                    tokens_used = getattr(event, "tokens_used", 0)
                    
                    # Tạo dữ liệu gửi đi
                    data = {
                        "content": new_text,
                        "done": event.is_final_response()
                    }
                    
                    # Thêm metadata cho sự kiện cuối cùng
                    if event.is_final_response():
                        data["metadata"] = {
                            "tokens_used": tokens_used,
                            "model_name": "gemini-2.0-flash-001",
                            "user_id": user_id,
                            "session_id": session_id,
                            "timestamp": datetime.now().isoformat()
                        }
                    
                    # Gửi dữ liệu
                    logger.info(f"Stream: Trả về LLM response trực tiếp: {new_text[:50]}...")
                    yield f"data: {json.dumps(data)}\n\n"
                    
                    # Nếu đã hoàn thành, kết thúc
                    if event.is_final_response():
                        break
            
            except Exception as e:
                # Ghi log lỗi
                logger.error(f"Lỗi khi chạy model: {str(e)}")
                
                # Trả về tin nhắn chào đơn giản
                fallback_response = "Chào bạn, tôi là trợ lý mua sắm thông minh của trang web thương mại điện tử. Tôi có thể giúp gì cho bạn hôm nay?"
                
                # Gửi dữ liệu
                data = {
                    "content": fallback_response,
                    "done": True,
                    "metadata": {
                        "tokens_used": 0,
                        "model_name": "gemini-2.0-flash-001",
                        "user_id": user_id,
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                yield f"data: {json.dumps(data)}\n\n"
            
        except Exception as e:
            logger.error(f"Lỗi khi streaming: {str(e)}")
            error_data = {
                "error": True,
                "message": f"Lỗi khi xử lý stream: {str(e)}",
                "error_code": "STREAM_ERROR",
                "stack_trace": str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/chat/stream")
async def stream_chat_get(
    message: str = Query(..., description="Tin nhắn của người dùng"),
    user_id: Optional[str] = Query(None, description="ID của người dùng"),
    session_id: Optional[str] = Query(None, description="ID của phiên chat"),
    response_format: str = Query("text", description="Định dạng phản hồi"),
    include_raw_response: bool = Query(False, description="Bao gồm phản hồi gốc"),
    max_context_messages: int = Query(20, description="Giới hạn số lượng tin nhắn trong context"),
    user_profile_json: Optional[str] = Query(None, description="Thông tin người dùng dạng JSON"),
    auth_token: Optional[str] = Query(None, description="Token xác thực (không sử dụng)"),
    _t: Optional[str] = Query(None, description="Timestamp cho cache busting (không sử dụng)"),
):
    # Chuyển đổi user_profile_json sang Dict
    user_profile = None
    if user_profile_json:
        try:
            user_profile = json.loads(user_profile_json)
        except Exception as e:
            logger.warning(f"Lỗi khi chuyển đổi user_profile_json: {e}")
    
    # Tạo một đối tượng ChatRequest từ các tham số query
    chat_request = ChatRequest(
        message=message,
        user_id=user_id,
        session_id=session_id,
        response_format=response_format,
        include_raw_response=include_raw_response,
        max_context_messages=max_context_messages,
        stream=True,
        user_profile=user_profile
    )
    
    # Gọi endpoint stream_chat với đối tượng ChatRequest
    return await stream_chat(chat_request)

@app.post("/api/reset-session")
async def reset_session(user_id: str, keep_profile: bool = True, user_profile_json: Optional[str] = None):
    """Reset phiên chat và tạo phiên mới, có thể giữ lại thông tin profile từ frontend."""
    try:
        # Tạo session_id mới
        new_session_id = str(uuid.uuid4())
        
        # Tạo phiên mới
        session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=new_session_id)
        
        # Tạo key cho dictionary toàn cục
        profile_key = f"{user_id}:{new_session_id}"
        
        # Cập nhật profile từ frontend nếu có
        user_profile = None
        if user_profile_json:
            try:
                user_profile = json.loads(user_profile_json)
                # Lưu profile vào dictionary toàn cục
                user_profiles[profile_key] = user_profile
                logger.info(f"Đã cập nhật profile từ frontend cho {profile_key}")
            except Exception as e:
                logger.warning(f"Lỗi khi cập nhật profile từ frontend: {e}")
                logger.exception(e)  # Log full traceback
        
        return {
            "success": True,
            "message": "Đã tạo phiên mới",
            "data": {
                "user_id": user_id,
                "session_id": new_session_id,
                "profile_updated": user_profile is not None
            }
        }
    except Exception as e:
        logger.error(f"Lỗi khi reset phiên: {str(e)}")
        logger.exception(e)  # Log full traceback
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": f"Lỗi khi reset phiên: {str(e)}",
                "error_code": "SESSION_RESET_ERROR",
                "error_details": {
                    "stack_trace": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

@app.post("/api/user-profile")
async def update_user_profile(
    user_id: str = Query(..., description="ID của người dùng"),
    session_id: str = Query(..., description="ID của phiên chat"),
    user_profile: Dict[str, Any] = None
):
    """API endpoint để cập nhật thông tin profile người dùng từ frontend."""
    try:
        # Tạo key cho dictionary toàn cục
        profile_key = f"{user_id}:{session_id}"
        
        # Kiểm tra xem session có tồn tại không
        try:
            session = session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
            logger.info(f"Đã tìm thấy session cho {profile_key}")
        except Exception as e:
            logger.warning(f"Session không tồn tại, tạo session mới: {e}")
            try:
                # Tạo session mới trước khi sử dụng
                session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
                session = session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
                logger.info(f"Đã tạo session mới cho {profile_key}")
            except Exception as e:
                logger.error(f"Không thể tạo session mới: {e}")
                logger.exception(e)  # Log full traceback
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "success": False,
                        "message": f"Không thể tạo session: {str(e)}",
                        "error_code": "SESSION_ERROR",
                        "error_details": {
                            "stack_trace": str(e),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                )
        
        # Cập nhật user_profile vào dictionary toàn cục
        if user_profile:
            user_profiles[profile_key] = user_profile
            logger.info(f"Đã cập nhật profile cho {profile_key}: {user_profile}")
            
            return {
                "success": True,
                "message": "Cập nhật thông tin profile thành công",
                "data": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "user_profile": user_profile
                }
            }
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "message": "Không có thông tin profile để cập nhật",
                    "error_code": "MISSING_PROFILE_DATA"
                }
            )
        
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật thông tin profile: {str(e)}")
        logger.exception(e)  # Log full traceback
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": f"Lỗi khi cập nhật thông tin profile: {str(e)}",
                "error_code": "PROFILE_ERROR",
                "error_details": {
                    "stack_trace": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

@app.get("/api/user-profile")
async def get_user_profile_get(
    user_id: str = Query(..., description="ID của người dùng"),
    session_id: str = Query(..., description="ID của phiên chat")
):
    """API endpoint GET để lấy thông tin profile người dùng."""
    try:
        # Tạo key cho dictionary toàn cục
        profile_key = f"{user_id}:{session_id}"
        
        # Kiểm tra xem session có tồn tại không
        try:
            session = session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
            logger.info(f"Đã tìm thấy session cho {profile_key}")
        except Exception as e:
            logger.warning(f"Session không tồn tại, tạo session mới: {e}")
            try:
                # Tạo session mới trước khi sử dụng
                session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
                session = session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
                logger.info(f"Đã tạo session mới cho {profile_key}")
            except Exception as e:
                logger.error(f"Không thể tạo session mới: {e}")
                logger.exception(e)  # Log full traceback
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "success": False,
                        "message": f"Không thể tạo session: {str(e)}",
                        "error_code": "SESSION_ERROR",
                        "error_details": {
                            "stack_trace": str(e),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                )
        
        # Lấy profile từ dictionary toàn cục
        user_profile = user_profiles.get(profile_key, {})
        logger.info(f"Lấy profile cho {profile_key}: {user_profile}")
        
        return {
            "success": True,
            "message": "Lấy thông tin profile thành công",
            "data": {
                "user_id": user_id,
                "session_id": session_id,
                "user_profile": user_profile
            }
        }
        
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin profile trong GET: {str(e)}")
        logger.exception(e)  # Log full traceback
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": f"Lỗi khi lấy thông tin profile: {str(e)}",
                "error_code": "PROFILE_ERROR",
                "error_details": {
                    "stack_trace": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

@app.get("/api/session-memory")
async def get_session_memory(
    user_id: str = Query(..., description="ID của người dùng"),
    session_id: str = Query(..., description="ID của phiên chat")
):
    """
    Lấy dữ liệu in-memory của một phiên chat.
    
    Args:
        user_id: ID của người dùng
        session_id: ID của phiên chat
        
    Returns:
        Dữ liệu in-memory của phiên chat
    """
    try:
        # Tạo session_key từ user_id và session_id
        session_key = f"{user_id}:{session_id}"
        logger.info(f"Nhận yêu cầu lấy session memory cho {session_key}")
        
        # Lấy thông tin user profile từ dictionary toàn cục
        user_profile = get_user_profile(user_id, session_id)
        logger.info(f"Đã lấy user profile: {user_profile}")
        
        # Lấy lịch sử hội thoại từ các nguồn khác nhau
        conversation_data = {"messages": [], "message_count": 0}
        try:
            # 1. Thử lấy từ session_data - không dùng await vì _get_session_data là hàm đồng bộ
            session_data = _get_session_data(session_id)
            logger.info(f"Đã lấy session_data: {session_data}")
            
            # Nếu session_data có messages, sử dụng nó
            if session_data and 'messages' in session_data and isinstance(session_data['messages'], list):
                conversation_data = {
                    "messages": session_data['messages'],
                    "message_count": len(session_data['messages'])
                }
                logger.info(f"Đã lấy {len(session_data['messages'])} tin nhắn từ session_data")
            # Nếu không có messages, tạo dữ liệu giả
            else:
                # Mô phỏng một số tin nhắn gần đây từ user_profiles
                messages = []
                
                # 2. Nếu có user_profile với các thông tin chi tiết, tạo một cuộc hội thoại đơn giản
                if user_profile:
                    # Thêm tin nhắn chào đầu tiên
                    welcome_msg = {
                        "role": "assistant",
                        "content": f"Xin chào, tôi là trợ lý mua sắm MM A2A. Tôi có thể giúp gì cho bạn?",
                        "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat()
                    }
                    messages.append(welcome_msg)
                    
                    # Nếu có viewed_products, thêm thông tin về sản phẩm đã xem
                    if 'viewed_products' in user_profile and user_profile['viewed_products']:
                        viewed_products = user_profile['viewed_products']
                        if isinstance(viewed_products, list) and len(viewed_products) > 0:
                            user_msg = {
                                "role": "user",
                                "content": "Tôi muốn xem thông tin về sản phẩm.",
                                "timestamp": (datetime.now() - timedelta(minutes=3)).isoformat()
                            }
                            messages.append(user_msg)
                            
                            bot_msg = {
                                "role": "assistant",
                                "content": f"Bạn đã xem {len(viewed_products)} sản phẩm gần đây. Bạn có muốn biết thêm thông tin về sản phẩm nào không?",
                                "timestamp": (datetime.now() - timedelta(minutes=2)).isoformat()
                            }
                            messages.append(bot_msg)
                
                conversation_data = {
                    "messages": messages,
                    "message_count": len(messages),
                    "note": "Không có lịch sử hội thoại chính xác, đây là dữ liệu mô phỏng"
                }
                
                logger.info(f"Đã tạo {len(messages)} tin nhắn mô phỏng")
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin hội thoại: {str(e)}")
            logger.exception(e)
            conversation_data = {"error": str(e)}
        
        # Đóng gói kết quả
        result = {
            "success": True,
            "session_key": session_key,
            "session_data": session_data if 'session_data' in locals() else {},
            "user_profile": user_profile,
            "conversation": conversation_data,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Trả về kết quả session memory thành công")
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu in-memory: {str(e)}")
        logger.exception(e)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Lỗi khi lấy dữ liệu in-memory: {str(e)}",
                "error_code": "MEMORY_FETCH_ERROR"
            }
        )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Lỗi không xử lý được: {str(exc)}")
    logger.exception(exc)  # Log full traceback
    import traceback
    stack_trace = ''.join(traceback.format_tb(exc.__traceback__))
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False, 
            "message": f"Lỗi hệ thống: {str(exc)}",
            "error_code": "SERVER_ERROR",
            "error_details": {
                "stack_trace": stack_trace,
                "error": str(exc),
                "timestamp": datetime.now().isoformat()
            }
        }
    )

@app.get("/api/get-port")
async def get_current_port():
    """Trả về thông tin về cổng hiện tại server đang chạy"""
    try:
        # Lấy cổng hiện tại từ app.state
        current_port = getattr(app.state, "port", active_config.SERVER_PORT)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "port": current_port,
                "host": active_config.SERVER_HOST
            }
        )
    except Exception as e:
        logger.error(f"Lỗi khi truy xuất thông tin cổng: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            content={
                "success": False,
                "message": f"Lỗi khi truy xuất thông tin cổng: {str(e)}",
                "error_code": "PORT_ERROR"
            }
        )

def start_server():
    """Khởi động server với Uvicorn."""
    import socket
    import uvicorn
    from config import active_config
    
    # Sử dụng cổng mặc định từ cấu hình
    port = active_config.SERVER_PORT
    host = active_config.SERVER_HOST
    
    # Kiểm tra xem cổng mặc định có sẵn sàng không
    available_port = None
    current_port = None
    
    # Sử dụng dải cổng từ cấu hình
    for port_to_try in active_config.PORT_RANGE:
        try:
            # Thử kết nối đến cổng để kiểm tra tính khả dụng
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)  # Timeout nhanh
            result = sock.connect_ex((host, port_to_try))
            sock.close()
            
            # Nếu kết nối không được thiết lập, cổng đã sẵn sàng
            if result != 0:
                available_port = port_to_try
                break
            else:
                logger.warning(f"Cổng {port_to_try} đã được sử dụng, thử cổng khác...")
        except Exception as e:
            logger.warning(f"Lỗi khi kiểm tra cổng {port_to_try}: {e}")
    
    if available_port:
        current_port = available_port
        logger.info(f"Sử dụng cổng khả dụng: {current_port}")
    else:
        current_port = active_config.PORT_RANGE[-1]  # Sử dụng cổng cuối cùng trong dải
        logger.warning(f"Không tìm thấy cổng khả dụng trong dải, sử dụng cổng cuối cùng: {current_port}")
        logger.warning("Server có thể không khởi động được nếu cổng này đã được sử dụng!")
    
    # Lưu cổng hiện tại để các phần khác có thể truy cập
    app.state.port = current_port
    
    # Bắt đầu Uvicorn
    logger.info(f"Khởi động server trên {host}:{current_port}...")
    uvicorn.run(
        "backend_server:app",
        host=host,
        port=current_port,
        reload=False,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    start_server() 