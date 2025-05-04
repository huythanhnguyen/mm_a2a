# Hướng dẫn sử dụng MM A2A Ecommerce Chatbot

## Các lỗi đã được sửa

1. **Lỗi import `root_agent`**:
   - Đã thêm export `root_agent` vào file `mm_a2a/agent/__init__.py`

2. **Lỗi hiển thị tiếng Việt trong logging**:
   - Đã điều chỉnh cấu hình logging để xử lý đúng Unicode trong tiếng Việt
   - Thêm `sys.stdout.reconfigure(encoding='utf-8')` để đảm bảo hiển thị đúng tiếng Việt

3. **Vấn đề với Google API Key**:
   - Đảm bảo Google API Key được thiết lập đúng trong file .env
   - Điều chỉnh logic để tránh lỗi khi không có key

4. **Cấu trúc callback không phù hợp**:
   - Điều chỉnh phương thức `start_cli()` để sử dụng đúng cách gọi API của Google ADK

5. **Đường dẫn không chính xác đến file sample_scenario.json**:
   - Đã sửa đường dẫn trong file `memory.py` để tìm chính xác file trong thư mục `eval`

## Hướng dẫn chạy

### 1. Phiên bản đơn giản (không cần Google API Key)

Nếu bạn chỉ muốn thử nghiệm chatbot với các câu trả lời cố định, sử dụng:

```bash
python simple_bot.py
```

### 2. Thử nghiệm tìm kiếm cá hồi đơn giản

Phiên bản đơn giản giả lập việc tìm kiếm cá hồi và thêm vào giỏ hàng:

```bash
python test_salmon_simple.py
```

### 3. Thử nghiệm tìm kiếm cá hồi với API thật

Phiên bản đầy đủ gọi API thực tế để tìm kiếm và thêm cá hồi vào giỏ hàng:

```bash
python test_salmon.py
```

### 4. Chạy chatbot đầy đủ

Khởi chạy chatbot đầy đủ với Google Gemini và API MM Ecommerce:

```bash
python main.py
```

Để chạy trong chế độ debug:

```bash
python main.py --debug
```

Để chạy như một API server:

```bash
python main.py --api
```

## Cấu hình

### File .env

Đảm bảo file `.env` chứa các cấu hình sau:

```
# API Keys
GOOGLE_API_KEY=your_google_api_key

# API Configurations
MM_ECOMMERCE_API_URL=https://online.mmvietnam.com/graphql
API_TIMEOUT=30
MM_STORE_CODE=b2c_10010_vi

# Environment Settings
ENV=development
DEBUG=True
LOG_LEVEL=DEBUG

# Server Settings
SERVER_HOST=0.0.0.0
SERVER_PORT=5000

# Other Configurations
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY=2
SESSION_TIMEOUT=1800
```

## Kiểm tra môi trường

Để kiểm tra môi trường và xác nhận rằng mọi thứ đã được cài đặt đúng:

```bash
python run_test.py
```

## Khắc phục sự cố

1. **Lỗi tiếng Việt không hiển thị đúng**:
   - Đảm bảo terminal của bạn sử dụng UTF-8
   - Trên Windows, sử dụng lệnh `chcp 65001` trước khi chạy ứng dụng

2. **Lỗi "No module named 'aiohttp'"**:
   - Cài đặt thư viện thiếu: `pip install aiohttp`
   - Hoặc cài đặt tất cả thư viện cần thiết: `pip install -r requirements.txt`

3. **Lỗi "Cannot import name 'root_agent'"**:
   - Nếu lỗi vẫn xuất hiện sau khi sửa, hãy khởi động lại Python interpreter
   - Hoặc sử dụng lệnh: `python -c "from mm_a2a.agent.agent import root_agent; print(root_agent)"`

4. **Lỗi API**:
   - Kiểm tra kết nối mạng
   - Xác nhận API URLs trong file .env
   - Kiểm tra logs để biết thêm chi tiết về lỗi
