#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Công cụ 'ghi nhớ' cho các agent để ảnh hưởng đến trạng thái phiên."""

from datetime import datetime
import json
import os
from typing import Dict, Any, List, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.sessions.state import State
from google.adk.tools import ToolContext

from mm_a2a.tools import constants

import logging

logger = logging.getLogger(__name__)

# Đường dẫn mặc định đến file sample_scenario.json
SAMPLE_SCENARIO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    os.getenv("MM_A2A_SCENARIO", "eval/sample_scenario.json")
)

# In-memory storage for simplicity in this prototype
# In a production setting, this should be replaced with a proper database
_memory_store = {}
_session_store = {}

def memorize_list(key: str, value: str, tool_context: ToolContext):
    """
    Ghi nhớ các mảng thông tin.

    Args:
        key: nhãn chỉ mục bộ nhớ để lưu trữ giá trị.
        value: thông tin cần được lưu trữ.
        tool_context: Ngữ cảnh công cụ ADK.

    Returns:
        Thông báo trạng thái.
    """
    mem_dict = tool_context.state
    if key not in mem_dict:
        mem_dict[key] = []
    if value not in mem_dict[key]:
        mem_dict[key].append(value)
    return {"status": f'Đã lưu "{key}": "{value}"'}


def memorize(key: str, value: str, tool_context: ToolContext):
    """
    Ghi nhớ thông tin, một cặp khóa-giá trị mỗi lần.

    Args:
        key: nhãn chỉ mục bộ nhớ để lưu trữ giá trị.
        value: thông tin cần được lưu trữ.
        tool_context: Ngữ cảnh công cụ ADK.

    Returns:
        Thông báo trạng thái.
    """
    mem_dict = tool_context.state
    mem_dict[key] = value
    return {"status": f'Đã lưu "{key}": "{value}"'}


def forget(key: str, value: str, tool_context: ToolContext):
    """
    Xóa thông tin đã ghi nhớ.

    Args:
        key: nhãn chỉ mục bộ nhớ để xóa giá trị.
        value: thông tin cần xóa.
        tool_context: Ngữ cảnh công cụ ADK.

    Returns:
        Thông báo trạng thái.
    """
    if tool_context.state[key] is None:
        tool_context.state[key] = []
    if value in tool_context.state[key]:
        tool_context.state[key].remove(value)
    return {"status": f'Đã xóa "{key}": "{value}"'}


def _set_initial_states(source: Dict[str, Any], target: State | dict[str, Any]):
    """
    Thiết lập trạng thái phiên ban đầu dựa trên đối tượng JSON của các trạng thái.

    Args:
        source: Đối tượng JSON của các trạng thái.
        target: Đối tượng trạng thái phiên để chèn vào.
    """
    if constants.SYSTEM_TIME not in target:
        target[constants.SYSTEM_TIME] = str(datetime.now())

    if constants.SESSION_INITIALIZED not in target:
        target[constants.SESSION_INITIALIZED] = True

        target.update(source)

        session_data = source.get(constants.SESSION_KEY, {})
        if session_data:
            target[constants.USER_ID] = session_data.get(constants.USER_ID, "")
            target[constants.SESSION_DATE] = session_data.get(constants.SESSION_DATE, "")


def _load_precreated_session(callback_context: CallbackContext):
    """
    Thiết lập trạng thái ban đầu.
    Đặt điều này như một callback before_agent_call của root_agent.
    Điều này được gọi trước khi tạo hướng dẫn hệ thống.

    Args:
        callback_context: Ngữ cảnh callback.
    """    
    data = {}
    with open(SAMPLE_SCENARIO_PATH, "r") as file:
        data = json.load(file)
        print(f"\nĐang tải trạng thái ban đầu: {data}\n")

    _set_initial_states(data["state"], callback_context.state)

async def memorize(key: str, value: str) -> Dict[str, Any]:
    """
    Lưu trữ một cặp key-value vào bộ nhớ phiên.
    
    Args:
        key: Khóa để lưu trữ giá trị.
        value: Giá trị cần lưu trữ.
        
    Returns:
        Dict[str, Any]: Kết quả lưu trữ.
    """
    try:
        _memory_store[key] = value
        logger.debug(f"Đã lưu giá trị cho khóa '{key}'")
        
        return {
            "success": True,
            "message": f"Đã lưu giá trị cho khóa '{key}'",
            "key": key
        }
    except Exception as e:
        logger.error(f"Lỗi khi lưu giá trị: {str(e)}")
        return {
            "success": False,
            "message": f"Lỗi khi lưu giá trị: {str(e)}",
            "key": key
        }

async def memorize_list(key: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Lưu trữ một danh sách các item vào bộ nhớ phiên.
    
    Args:
        key: Khóa để lưu trữ danh sách.
        items: Danh sách các item cần lưu trữ.
        
    Returns:
        Dict[str, Any]: Kết quả lưu trữ.
    """
    try:
        _memory_store[key] = json.dumps(items)
        logger.debug(f"Đã lưu danh sách với {len(items)} item vào khóa '{key}'")
        
        return {
            "success": True,
            "message": f"Đã lưu danh sách với {len(items)} item vào khóa '{key}'",
            "key": key,
            "count": len(items)
        }
    except Exception as e:
        logger.error(f"Lỗi khi lưu danh sách: {str(e)}")
        return {
            "success": False,
            "message": f"Lỗi khi lưu danh sách: {str(e)}",
            "key": key
        }

async def get_memory(key: str) -> Dict[str, Any]:
    """
    Lấy giá trị từ bộ nhớ phiên theo khóa.
    
    Args:
        key: Khóa để lấy giá trị.
        
    Returns:
        Dict[str, Any]: Kết quả truy xuất.
    """
    try:
        if key in _memory_store:
            value = _memory_store[key]
            # Thử phân tích JSON nếu có thể
            try:
                parsed_value = json.loads(value)
                logger.debug(f"Đã lấy giá trị JSON cho khóa '{key}'")
                return {
                    "success": True,
                    "message": f"Đã lấy giá trị cho khóa '{key}'",
                    "key": key,
                    "value": parsed_value,
                    "is_json": True
                }
            except:
                # Không phải JSON, trả về nguyên bản
                logger.debug(f"Đã lấy giá trị chuỗi cho khóa '{key}'")
                return {
                    "success": True,
                    "message": f"Đã lấy giá trị cho khóa '{key}'",
                    "key": key,
                    "value": value,
                    "is_json": False
                }
        else:
            logger.warning(f"Không tìm thấy giá trị cho khóa '{key}'")
            return {
                "success": False,
                "message": f"Không tìm thấy giá trị cho khóa '{key}'",
                "key": key
            }
    except Exception as e:
        logger.error(f"Lỗi khi lấy giá trị: {str(e)}")
        return {
            "success": False,
            "message": f"Lỗi khi lấy giá trị: {str(e)}",
            "key": key
        }

def _get_from_memory(key: str) -> Optional[str]:
    """
    Hàm nội bộ để lấy giá trị từ bộ nhớ phiên.
    
    Args:
        key: Khóa cần lấy.
        
    Returns:
        Optional[str]: Giá trị tương ứng hoặc None nếu không tìm thấy.
    """
    return _memory_store.get(key)

def _store_session_data(session_id: str, data: Dict[str, Any]):
    """
    Lưu trữ dữ liệu phiên dựa trên ID phiên.
    
    Args:
        session_id: ID của phiên.
        data: Dữ liệu cần lưu trữ.
    """
    _session_store[session_id] = data

def _get_session_data(session_id: str) -> Dict[str, Any]:
    """
    Lấy dữ liệu phiên dựa trên ID phiên.
    
    Args:
        session_id: ID của phiên.
        
    Returns:
        Dict[str, Any]: Dữ liệu phiên hoặc dict rỗng nếu không tìm thấy.
    """
    return _session_store.get(session_id, {})

async def _load_precreated_session(context=None, callback_context=None):
    """
    Tải dữ liệu phiên đã tạo sẵn vào session hiện tại.
    Callback được sử dụng trước khi agent chạy.
    
    Args:
        context: Context của agent (cũ).
        callback_context: Context của callback (mới).
    """
    try:
        # Sử dụng context hoặc callback_context tùy vào cái nào có sẵn
        ctx = callback_context or context
        
        if ctx and hasattr(ctx, 'session') and ctx.session:
            session_id = ctx.session.session_id
            saved_data = _get_session_data(session_id)
            
            if saved_data:
                # Khôi phục dữ liệu vào session state
                for key, value in saved_data.items():
                    ctx.session.state[key] = value
                
                logger.info(f"Đã tải {len(saved_data)} khóa từ phiên {session_id}")
                
                # Đặc biệt kiểm tra cart_id
                if 'cart_id' in saved_data:
                    logger.info(f"Khôi phục giỏ hàng {saved_data['cart_id']}")
                    
                    # Lưu cart_id vào memory store để các agent khác có thể truy cập
                    # Không dùng await với session object
                    _memory_store['cart_id'] = saved_data['cart_id']
                    logger.debug(f"Đã lưu giá trị cart_id trực tiếp vào memory store")
    except Exception as e:
        logger.error(f"Lỗi khi tải phiên đã tạo sẵn: {str(e)}")
        logger.exception(e)

async def _save_session_data(context=None, callback_context=None):
    """
    Lưu dữ liệu phiên hiện tại.
    Callback được sử dụng sau khi agent chạy.
    
    Args:
        context: Context của agent (cũ).
        callback_context: Context của callback (mới).
    """
    try:
        # Sử dụng context hoặc callback_context tùy vào cái nào có sẵn
        ctx = callback_context or context
        
        if ctx and hasattr(ctx, 'session') and ctx.session:
            session_id = ctx.session.session_id
            # Lấy toàn bộ state hiện tại
            data_to_save = dict(ctx.session.state)
            
            # Thêm lịch sử tin nhắn vào dữ liệu lưu trữ
            messages = []
            if hasattr(ctx.session, 'history') and ctx.session.history:
                for msg in ctx.session.history:
                    if hasattr(msg, 'role') and hasattr(msg, 'parts') and len(msg.parts) > 0:
                        try:
                            content = msg.parts[0].text if hasattr(msg.parts[0], 'text') else str(msg.parts[0])
                            messages.append({
                                "role": msg.role,
                                "content": content,
                                "timestamp": datetime.now().isoformat()
                            })
                            logger.info(f"Đã lưu tin nhắn: {msg.role} - {content[:30]}...")
                        except Exception as e:
                            logger.error(f"Lỗi khi xử lý tin nhắn: {str(e)}")
                            continue
            
            # Thêm messages vào dữ liệu lưu trữ
            data_to_save['messages'] = messages
            logger.info(f"Đã thêm {len(messages)} tin nhắn vào dữ liệu lưu trữ")
            
            # Lọc bỏ các giá trị quá lớn hoặc không cần thiết
            filtered_data = {}
            for key, value in data_to_save.items():
                # Bỏ qua các khóa bắt đầu bằng "_" (thường là nội bộ)
                if key.startswith("_"):
                    continue
                    
                try:
                    # Xử lý các giá trị đặc biệt tùy theo loại
                    if key == 'messages':
                        # Đối với tin nhắn, lưu trữ trực tiếp
                        filtered_data[key] = value
                    elif isinstance(value, str) and len(value) > 10000:
                        # Bỏ qua các giá trị quá lớn để tránh tràn bộ nhớ
                        filtered_data[key + "_summary"] = f"Large value: {len(value)} chars"
                    else:
                        # Thử chuyển đổi thành JSON để kiểm tra khả năng serialize
                        try:
                            json.dumps(value)
                            filtered_data[key] = value
                        except (TypeError, OverflowError, ValueError):
                            # Nếu không thể serialize, lưu tóm tắt về loại đối tượng
                            filtered_data[key + "_type"] = f"Non-serializable {type(value).__name__}"
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý khóa {key}: {str(e)}")
                    continue
            
            # Lưu dữ liệu đã lọc
            _store_session_data(session_id, filtered_data)
            logger.info(f"Đã lưu {len(filtered_data)} khóa vào phiên {session_id}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu dữ liệu phiên: {str(e)}")
        logger.exception(e)
