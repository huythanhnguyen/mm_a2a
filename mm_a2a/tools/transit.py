#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Công cụ xử lý vận chuyển và điều phối cho MM A2A Ecommerce Chatbot.
Lấy ý tưởng từ transit_coordination trong Google Travel Concierge.
"""

from datetime import datetime
from typing import Dict, Any

from google.adk.agents.readonly_context import ReadonlyContext

from mm_a2a.tools import constants
from mm_a2a import prompt


def get_event_time(event_json: Dict[str, Any], default_value: str) -> str:
    """
    Trả về thời gian sự kiện phù hợp với loại sự kiện.
    
    Args:
        event_json: Đối tượng JSON chứa thông tin sự kiện.
        default_value: Giá trị mặc định nếu không tìm thấy thời gian phù hợp.
        
    Returns:
        Chuỗi thời gian phù hợp với loại sự kiện.
    """
    event_type = event_json.get("event_type", "")
    
    if event_type == "order":
        return event_json.get("delivery_time", default_value)
    elif event_type == "payment":
        return event_json.get("payment_time", default_value)
    elif event_type == "delivery":
        return event_json.get("estimated_arrival", default_value)
    else:
        return default_value


def parse_as_origin(origin_json: Dict[str, Any]) -> tuple:
    """
    Trả về tuple (origin, depart_by) phù hợp cho điểm xuất phát.
    
    Args:
        origin_json: Đối tượng JSON chứa thông tin điểm xuất phát.
        
    Returns:
        Tuple chứa thông tin điểm xuất phát và thời gian khởi hành.
    """
    event_type = origin_json.get("event_type", "")
    
    if event_type == "order":
        return (
            f"Order placed at {origin_json.get('store_name', 'store')}",
            origin_json.get("order_time", "any time")
        )
    elif event_type == "payment":
        return (
            f"Payment made for order #{origin_json.get('order_id', 'unknown')}",
            origin_json.get("payment_time", "any time")
        )
    elif event_type == "delivery":
        return (
            f"Delivery from {origin_json.get('store_name', 'store')}",
            origin_json.get("shipping_time", "any time")
        )
    elif event_type == "home":
        return (
            f"Customer home at {origin_json.get('address', 'unknown address')}",
            "any time"
        )
    else:
        return "Unknown origin", "any time"


def parse_as_destination(destin_json: Dict[str, Any]) -> tuple:
    """
    Trả về tuple (destination, arrive_by) phù hợp cho điểm đến.
    
    Args:
        destin_json: Đối tượng JSON chứa thông tin điểm đến.
        
    Returns:
        Tuple chứa thông tin điểm đến và thời gian đến.
    """
    event_type = destin_json.get("event_type", "")
    
    if event_type == "order":
        return (
            f"Order #{destin_json.get('order_id', 'unknown')} confirmation",
            destin_json.get("confirmation_time", "soon")
        )
    elif event_type == "payment":
        return (
            f"Payment confirmation for order #{destin_json.get('order_id', 'unknown')}",
            "immediately after payment"
        )
    elif event_type == "delivery":
        return (
            f"Delivery to {destin_json.get('address', 'customer address')}",
            destin_json.get("estimated_arrival", "as scheduled")
        )
    elif event_type == "home":
        return (
            f"Customer home at {destin_json.get('address', 'unknown address')}",
            "any time"
        )
    else:
        return "Unknown destination", "as soon as possible"


def find_next_event(customer_profile: Dict[str, Any], order_history: Dict[str, Any], current_datetime: str) -> tuple:
    """
    Tìm sự kiện tiếp theo từ A đến B dựa trên lịch sử đơn hàng.
    
    Args:
        customer_profile: Đối tượng JSON chứa thông tin khách hàng.
        order_history: Đối tượng JSON chứa lịch sử đơn hàng.
        current_datetime: Chuỗi chứa ngày và thời gian hiện tại.
        
    Returns:
        Tuple chứa thông tin về nguồn gốc, điểm đến, thời gian rời đi và thời gian đến.
    """
    # Chuyển đổi định dạng thời gian
    datetime_object = datetime.fromisoformat(current_datetime)
    current_date = datetime_object.strftime("%Y-%m-%d")
    current_time = datetime_object.strftime("%H:%M")
    
    # Giá trị mặc định
    origin_json = customer_profile.get("home", {})
    destin_json = customer_profile.get("home", {})
    
    leave_by = "Không cần di chuyển"
    arrive_by = "Không cần di chuyển"
    
    # Duyệt qua lịch sử đơn hàng để tìm sự kiện tiếp theo
    for order in order_history.get("orders", []):
        order_date = order.get("order_date", "")
        
        # Duyệt qua các sự kiện trong đơn hàng
        for event in order.get("events", []):
            origin_json = destin_json
            destin_json = event
            event_time = get_event_time(destin_json, current_time)
            
            # Tìm sự kiện trong tương lai gần
            if order_date >= current_date and event_time >= current_time:
                break
        else:
            continue
        break
    
    # Xây dựng mô tả
    travel_from, leave_by = parse_as_origin(origin_json)
    travel_to, arrive_by = parse_as_destination(destin_json)
    
    return (travel_from, travel_to, leave_by, arrive_by)


def _inspect_order_history(state: dict) -> tuple:
    """
    Xác định và trả về lịch sử đơn hàng, hồ sơ khách hàng và thời gian hiện tại từ trạng thái phiên.
    
    Args:
        state: Đối tượng trạng thái phiên.
        
    Returns:
        Tuple chứa lịch sử đơn hàng, hồ sơ khách hàng và thời gian hiện tại.
    """
    order_history = state.get(constants.ORDER_HISTORY_KEY, {})
    customer_profile = state.get(constants.CUSTOMER_PROFILE_KEY, {})
    
    # Mặc định thời gian hiện tại
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if state.get(constants.SYSTEM_TIME, ""):
        current_datetime = state[constants.SYSTEM_TIME]
    
    return order_history, customer_profile, current_datetime


def order_status_check(order_id: str, readonly_context: ReadonlyContext):
    """
    Kiểm tra trạng thái đơn hàng dựa trên ID đơn hàng.
    
    Args:
        order_id: ID của đơn hàng cần kiểm tra.
        readonly_context: Ngữ cảnh chỉ đọc.
        
    Returns:
        Đối tượng JSON chứa thông tin trạng thái đơn hàng.
    """
    state = readonly_context.state
    order_history = state.get(constants.ORDER_HISTORY_KEY, {})
    
    # Tìm đơn hàng theo ID
    for order in order_history.get("orders", []):
        if order.get("order_id", "") == order_id:
            return {
                "status": f"Đơn hàng #{order_id}",
                "order_status": order.get("status", "Không xác định"),
                "payment_status": order.get("payment_status", "Không xác định"),
                "delivery_status": order.get("delivery_status", "Không xác định"),
                "estimated_delivery": order.get("estimated_delivery", "Không xác định")
            }
    
    return {"status": f"Không tìm thấy đơn hàng #{order_id}"}


def payment_status_check(order_id: str, readonly_context: ReadonlyContext):
    """
    Kiểm tra trạng thái thanh toán của đơn hàng.
    
    Args:
        order_id: ID của đơn hàng cần kiểm tra.
        readonly_context: Ngữ cảnh chỉ đọc.
        
    Returns:
        Đối tượng JSON chứa thông tin trạng thái thanh toán.
    """
    state = readonly_context.state
    order_history = state.get(constants.ORDER_HISTORY_KEY, {})
    
    # Tìm đơn hàng theo ID
    for order in order_history.get("orders", []):
        if order.get("order_id", "") == order_id:
            return {
                "status": f"Thanh toán cho đơn hàng #{order_id}",
                "payment_status": order.get("payment_status", "Không xác định"),
                "payment_method": order.get("payment_method", "Không xác định"),
                "transaction_id": order.get("transaction_id", "Không xác định"),
                "payment_date": order.get("payment_date", "Không xác định")
            }
    
    return {"status": f"Không tìm thấy thông tin thanh toán cho đơn hàng #{order_id}"}


def delivery_status_check(order_id: str, readonly_context: ReadonlyContext):
    """
    Kiểm tra trạng thái giao hàng của đơn hàng.
    
    Args:
        order_id: ID của đơn hàng cần kiểm tra.
        readonly_context: Ngữ cảnh chỉ đọc.
        
    Returns:
        Đối tượng JSON chứa thông tin trạng thái giao hàng.
    """
    state = readonly_context.state
    order_history = state.get(constants.ORDER_HISTORY_KEY, {})
    
    # Tìm đơn hàng theo ID
    for order in order_history.get("orders", []):
        if order.get("order_id", "") == order_id:
            return {
                "status": f"Giao hàng cho đơn hàng #{order_id}",
                "delivery_status": order.get("delivery_status", "Không xác định"),
                "tracking_number": order.get("tracking_number", "Không xác định"),
                "shipping_method": order.get("shipping_method", "Không xác định"),
                "estimated_delivery": order.get("estimated_delivery", "Không xác định"),
                "delivery_address": order.get("delivery_address", "Không xác định")
            }
    
    return {"status": f"Không tìm thấy thông tin giao hàng cho đơn hàng #{order_id}"}


def order_coordination(readonly_context: ReadonlyContext):
    """
    Tạo hướng dẫn động cho agent quản lý đơn hàng.
    
    Args:
        readonly_context: Ngữ cảnh chỉ đọc.
        
    Returns:
        Chuỗi hướng dẫn cho agent quản lý đơn hàng.
    """
    state = readonly_context.state
    
    # Kiểm tra lịch sử đơn hàng
    if constants.ORDER_HISTORY_KEY not in state:
        return prompt.NEED_ORDER_HISTORY_INSTR
    
    order_history, customer_profile, current_datetime = _inspect_order_history(state)
    travel_from, travel_to, leave_by, arrive_by = find_next_event(
        customer_profile, order_history, current_datetime
    )
    
    return prompt.ORDER_INSTR_TEMPLATE.format(
        CURRENT_TIME=current_datetime,
        ORDER_FROM=travel_from,
        ORDER_TIME=leave_by,
        ORDER_TO=travel_to,
        ARRIVAL_TIME=arrive_by,
    )
