# API Client cho MM Ecommerce

API Client cho việc tương tác với API GraphQL của MM Ecommerce được cấu trúc theo module.

## Cấu trúc

```
api_client/
  ├── __init__.py           # Export các module
  ├── api_client.py         # EcommerceAPIClient - client chính tổng hợp
  ├── base.py               # APIClientBase - lớp cơ sở
  ├── product.py            # ProductAPI - module cho sản phẩm
  ├── cart.py               # CartAPI - module cho giỏ hàng
  ├── auth.py               # AuthAPI - module cho xác thực
  ├── README.md             # Tài liệu
  ├── CHANGES.md            # Ghi chú phát triển
  └── tests.py              # Kiểm thử
```

## Cách sử dụng

```python
import asyncio
from mm_a2a.tools.api_client import EcommerceAPIClient

async def main():
    # Khởi tạo client
    client = EcommerceAPIClient(
        base_url="https://example.com/api",
        timeout=30  # timeout 30 giây
    )
    
    try:
        # Sử dụng như một async context manager
        async with client:
            # Tìm kiếm sản phẩm
            result = await client.search_products("bàn ăn", page_size=10)
            print(result)
            
            # Tạo giỏ hàng
            cart = await client.create_cart(is_guest=True)
            
            # Thêm sản phẩm vào giỏ hàng
            await client.add_to_cart(product_id="SKU123", quantity=2)
    finally:
        # Đóng session
        await client.close()

# Chạy
asyncio.run(main())
```

## Quản lý Session

API Client sử dụng `aiohttp.ClientSession` để quản lý các kết nối HTTP. Session được tạo tự động khi cần và được đóng khi gọi `close()` hoặc khi sử dụng với context manager.

### Sử dụng với Context Manager

```python
async with EcommerceAPIClient(base_url="https://example.com/api") as client:
    result = await client.search_products("bàn ăn")
```

### Sử dụng thủ công

```python
client = EcommerceAPIClient(base_url="https://example.com/api")
try:
    result = await client.search_products("bàn ăn")
finally:
    await client.close()  # Luôn đóng session
```

## Xử lý lỗi và Retry

API Client sử dụng thư viện `tenacity` để tự động thử lại các request thất bại với cơ chế exponential backoff.

## Các module

### ProductAPI

Module cung cấp các phương thức liên quan đến sản phẩm:

- `search_products`: Tìm kiếm sản phẩm
- `get_product_by_sku`: Lấy thông tin sản phẩm theo SKU
- `get_product_by_art_no`: Lấy thông tin sản phẩm theo Article Number
- `suggest_products`: Gợi ý sản phẩm với bộ lọc nâng cao
- `search_multiple_products`: Tìm kiếm nhiều từ khóa cùng lúc

### CartAPI

Module cung cấp các phương thức liên quan đến giỏ hàng:

- `create_cart`: Tạo giỏ hàng mới
- `add_to_cart`: Thêm sản phẩm vào giỏ hàng
- `get_cart_info`: Lấy thông tin giỏ hàng
- `update_cart_item`: Cập nhật số lượng sản phẩm trong giỏ hàng
- `remove_cart_item`: Xóa sản phẩm khỏi giỏ hàng

### AuthAPI

Module cung cấp các phương thức liên quan đến xác thực:

- `login`: Đăng nhập
- `login_with_mcard`: Đăng nhập bằng thông tin MCard
- `create_customer_from_mcard`: Tạo tài khoản từ thông tin MCard
- `get_token_lifetime`: Lấy thời gian sống của token
- `get_customer_info`: Lấy thông tin khách hàng
- `check_auth_status`: Kiểm tra trạng thái xác thực

## Cải tiến trong phiên bản mới

Thiết kế mới sử dụng mẫu composition thay vì kế thừa đa cấp để giải quyết vấn đề vòng lặp import. EcommerceAPIClient sử dụng các instances của các API modules riêng lẻ, đồng bộ hóa các thuộc tính chung như auth_token, cart_id, và store_code. 