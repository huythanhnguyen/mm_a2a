# MM A2A Ecommerce Chatbot

MM A2A Ecommerce Chatbot là một chatbot tương tác với API của MM Vietnam Ecommerce.

## Cài đặt

1. Clone repository
2. Cài đặt các gói phụ thuộc:

```bash
pip install -r requirements.txt
```

3. Tạo file `.env` và thiết lập các biến môi trường cần thiết:

```
GOOGLE_API_KEY=your_api_key_here
```

## Chạy ứng dụng

### Backend Server (Port 5000)

Có hai cách để chạy backend server:

1. Sử dụng file batch:

```bash
start_backend.bat
```

2. Chạy trực tiếp từ Python:

```bash
python backend_server.py
```

Server sẽ chạy trên `http://localhost:5000`

### Frontend Server (Port 8000)

Để chạy frontend server:

```bash
cd mm_front
python api_server.py
```

Frontend sẽ chạy trên `http://localhost:8000` và kết nối đến backend ở `http://localhost:5000`.

### Chạy CLI

Để chạy phiên bản dòng lệnh:

```bash
python main.py
```

## API Endpoints

### Backend API

- `GET /`: Trả về trạng thái của API server
- `GET /api/health`: Kiểm tra sức khỏe của server
- `POST /api/chat`: Gửi tin nhắn đến chatbot và nhận phản hồi

### Frontend API

- `GET /`: Trả về giao diện người dùng
- `POST /api/chat`: Proxy endpoint để gửi tin nhắn đến backend
- `GET /api/search-product`: Tìm kiếm sản phẩm

## Cấu trúc dự án

```
mm_a2a/
├─ mm_a2a/             # Mã nguồn chính
│  ├─ agent/           # Agent chính
│  ├─ sub_agents/      # Các sub-agent
│  │  ├─ cng/          # CnG Agent (Click and Get)
│  ├─ tools/           # Công cụ và hàm tiện ích
│  │  ├─ api_client/   # API client cho MM Ecommerce
├─ tools/              # Công cụ bổ sung
├─ mm_front/           # Frontend
├─ backend_server.py   # Backend server (port 5000)
├─ main.py             # CLI runner
├─ config.py           # Cấu hình ứng dụng
├─ requirements.txt    # Các phụ thuộc
```

## Kiến trúc

Dự án sử dụng kiến trúc agent-based với một root agent và nhiều sub-agent:

1. **Root Agent**: Điều phối các sub-agent khác
2. **CnG Agent**: Quản lý giỏ hàng và đặt hàng
3. **Product Agent**: Tìm kiếm và hiển thị thông tin sản phẩm
4. **Cart Manager Agent**: Quản lý giỏ hàng

Backend API phục vụ trên port 5000 sử dụng FastAPI và Uvicorn, kết nối tới các agent này để xử lý yêu cầu của người dùng.

## Phát triển

Tham khảo tệp `INSTRUCTIONS.md` để biết chi tiết về phát triển dự án.
