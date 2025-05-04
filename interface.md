# MM A2A Ecommerce Chatbot API Interface

## Tổng quan

MM A2A Ecommerce Chatbot API cung cấp các endpoint để tương tác với chatbot thông qua giao thức HTTP. API được xây dựng trên nền tảng FastAPI và chạy trên cổng 5000.

## Endpoints

### Kiểm tra trạng thái API

```
GET /
```

**Response:**
```json
{
  "message": "MM A2A Ecommerce Chatbot API đang hoạt động"
}
```

### Kiểm tra sức khỏe server

```
GET /api/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "MM A2A Ecommerce Chatbot API"
}
```

### Chat với Chatbot

```
POST /api/chat
```

#### Parameters

| Tham số | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---------|------|----------|----------|-------|
| user_id | string | Không | UUID mới | ID của người dùng |
| session_id | string | Không | UUID mới | ID của phiên chat |
| message | string | Có | - | Tin nhắn của người dùng |
| message_type | string | Không | "text" | Loại tin nhắn (hiện chỉ hỗ trợ "text") |
| stream | boolean | Không | false | Nếu true, phản hồi sẽ được gửi theo dạng stream |
| include_raw_response | boolean | Không | false | Nếu true, phản hồi sẽ bao gồm dữ liệu gốc từ model |
| include_session_data | boolean | Không | false | Nếu true, phản hồi sẽ bao gồm dữ liệu phiên chat |
| response_format | string | Không | "text" | Định dạng phản hồi ("text", "markdown", "html") |
| include_timestamps | boolean | Không | false | Nếu true, phản hồi sẽ bao gồm timestamp |
| include_thinking | boolean | Không | false | Nếu true, phản hồi sẽ bao gồm quá trình suy nghĩ của chatbot |
| max_tokens | integer | Không | null | Giới hạn số lượng token trong phản hồi |
| max_context_messages | integer | Không | 20 | Giới hạn số lượng tin nhắn trong context |

**Request Example:**
```json
{
  "user_id": "user-123",
  "session_id": "session-456",
  "message": "Tôi muốn tìm kiếm điện thoại Samsung",
  "include_session_data": true,
  "response_format": "markdown",
  "max_context_messages": 15
}
```

**Response Example:**
```json
{
  "success": true,
  "message": "Xử lý thành công",
  "data": {
    "response": "Tôi có thể giúp bạn tìm kiếm điện thoại Samsung. Bạn đang quan tâm đến dòng nào cụ thể như Galaxy S, Note hay A series?",
    "user_id": "user-123",
    "session_id": "session-456",
    "timestamp": "2023-06-15T08:30:45.123Z",
    "session_data": {
      "conversation_history": [
        {
          "role": "user",
          "content": "Tôi muốn tìm kiếm điện thoại Samsung",
          "timestamp": "2023-06-15T08:30:45.123Z"
        },
        {
          "role": "assistant",
          "content": "Tôi có thể giúp bạn tìm kiếm điện thoại Samsung. Bạn đang quan tâm đến dòng nào cụ thể như Galaxy S, Note hay A series?",
          "timestamp": "2023-06-15T08:30:45.678Z"
        }
      ],
      "memory": {
        "last_query": "product_search",
        "product_category": "smartphone"
      },
      "user_profile": {
        "name": "Nguyễn Văn A",
        "phone": "0912345678",
        "address": "Hà Nội",
        "shopping_preferences": ["điện thoại", "laptop"],
        "viewed_products": ["Samsung Galaxy S23"],
        "cart_items": []
      }
    }
  }
}
```

### Chat với Chatbot (Stream)

```
POST /api/chat/stream
```

```
GET /api/chat/stream?message=your_message&user_id=your_user_id&session_id=your_session_id
```

Tham số tương tự như endpoint `/api/chat`, nhưng phản hồi được gửi theo dạng Server-Sent Events (SSE) hoặc WebSocket.

Tham số bổ sung cho cả POST và GET:

| Tham số | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---------|------|----------|----------|-------|
| stream_format | string | Không | "sse" | Định dạng stream ("sse" hoặc "websocket") |
| instruction | string | Không | null | Hướng dẫn đặc biệt cho chatbot |
| memory | object | Không | null | Dữ liệu bộ nhớ từ phiên chat |

#### Phương thức GET

```
GET /api/chat/stream?message=your_message&user_id=your_user_id&session_id=your_session_id&instruction=your_instruction
```

#### Phương thức POST

```
POST /api/chat/stream
```

Body (JSON):
```json
{
  "user_id": "user-123",
  "session_id": "session-456",
  "message": "Tôi muốn tìm sản phẩm cá hồi",
  "instruction": "Hãy đề xuất các sản phẩm cá hồi phổ biến nhất",
  "memory": {
    "last_products_viewed": ["Xương cá hồi nhập khẩu"]
  },
  "stream_format": "sse"
}
```

### Stream Response Format (SSE)

Stream sẽ gửi nhiều sự kiện SSE, mỗi sự kiện có dạng:

```
data: {"content": "...", "done": boolean, "action": "...", "metadata": {...}}
```

Trong đó:
- `content`: Phần nội dung của phản hồi (có thể là text hoặc JSON string)
- `done`: Cờ đánh dấu đã hoàn thành phản hồi hay chưa
- `action`: Loại phản hồi (text, search_products, get_product_detail, ...)
- `metadata`: Dữ liệu bổ sung khi phản hồi hoàn thành

#### Ví dụ Stream Response (SSE)

**1. Stream phản hồi văn bản (action: "text")**

```
data: {"content": "Xin ", "done": false, "action": "text"}

data: {"content": "chào! ", "done": false, "action": "text"}

data: {"content": "Tôi ", "done": false, "action": "text"}

data: {"content": "có thể ", "done": false, "action": "text"}

data: {"content": "giúp gì ", "done": false, "action": "text"}

data: {"content": "cho bạn?", "done": true, "action": "text", "metadata": {"tokens_used": 15, "model_name": "gemini-2.0-flash-001", "user_id": "user-123", "session_id": "session-456"}}
```

**2. Stream phản hồi JSON (action: "search_products")**

```
data: {"content": "json\n{", "done": false, "action": "search_products"}

data: {"content": "\"products\": [", "done": false, "action": "search_products"}

data: {"content": "{\"product_id\": \"95652\", \"name\": \"Xương cá hồi nhập khẩu\", \"price\": 59000},", "done": false, "action": "search_products"}

data: {"content": "{\"product_id\": \"72319\", \"name\": \"Vây cá hồi nhập khẩu đông lạnh\", \"price\": 115000}", "done": false, "action": "search_products"}

data: {"content": "],", "done": false, "action": "search_products"}

data: {"content": "\"total_results\": 2116, \"page\": 1}", "done": true, "action": "search_products", "metadata": {"tokens_used": 42, "model_name": "gemini-2.0-flash-001", "user_id": "user-123", "session_id": "session-456"}}
```

### Stream Response Format (WebSocket)

WebSocket sẽ gửi tin nhắn JSON theo định dạng:

```json
{
  "content": "...",
  "done": boolean,
  "action": "...",
  "turn_complete": boolean,
  "metadata": {...}
}
```

Trong đó:
- `content`: Phần nội dung của phản hồi (có thể là text hoặc JSON string)
- `done`: Cờ đánh dấu đã hoàn thành phần nội dung hiện tại
- `action`: Loại phản hồi (text, search_products, get_product_detail, ...)
- `turn_complete`: Cờ đánh dấu đã hoàn thành lượt trả lời
- `metadata`: Dữ liệu bổ sung khi phản hồi hoàn thành

#### WebSocket Endpoint

```
ws://your-domain/ws/{session_id}
```

Kết nối WebSocket cho phép giao tiếp hai chiều real-time. Dữ liệu được gửi dưới dạng JSON string.

**Gửi tin nhắn từ client đến server:**

```json
{
  "message": "Tôi muốn tìm sản phẩm cá hồi",
  "user_id": "user-123",
  "instruction": "Hãy đề xuất các sản phẩm cá hồi phổ biến nhất"
}
```

**Nhận phản hồi từ server:**

```json
{
  "content": "Tôi đang tìm kiếm sản phẩm cá hồi cho bạn...",
  "done": false,
  "action": "text"
}
```

```json
{
  "content": "Đây là một số sản phẩm cá hồi phổ biến:",
  "done": true,
  "action": "text",
  "turn_complete": false
}
```

```json
{
  "content": "json\n{\"products\": [{\"product_id\": \"95652\", \"name\": \"Xương cá hồi nhập khẩu\", \"price\": 59000}]}",
  "done": true,
  "action": "search_products",
  "turn_complete": true,
  "metadata": {
    "tokens_used": 42,
    "model_name": "gemini-2.0-flash-001",
    "user_id": "user-123"
  }
}
```

### Tạo phiên mới

```
POST /api/reset-session
```

#### Parameters

| Tham số | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---------|------|----------|----------|-------|
| user_id | string | Có | - | ID của người dùng |
| keep_profile | boolean | Không | true | Nếu true, thông tin cá nhân của người dùng sẽ được giữ lại trong phiên mới |

**Request Example:**
```
POST /api/reset-session?user_id=user-123&keep_profile=true
```

**Response Example:**
```json
{
  "success": true,
  "message": "Đã tạo phiên mới",
  "data": {
    "user_id": "user-123",
    "session_id": "session-789",
    "profile_kept": true
  }
}
```

### Lấy dữ liệu in-memory của phiên chat

```
GET /api/session-memory
```

#### Parameters

| Tham số | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---------|------|----------|----------|-------|
| user_id | string | Có | - | ID của người dùng |
| session_id | string | Có | - | ID của phiên chat |

**Request Example:**
```
GET /api/session-memory?user_id=user-123&session_id=session-456
```

**Response Example:**
```json
{
  "success": true,
  "session_key": "user-123:session-456",
  "session_data": {
    "last_query": "product_search",
    "product_category": "smartphone",
    "last_products_viewed": ["Samsung Galaxy S23", "iPhone 15"]
  },
  "user_profile": {
    "name": "Nguyễn Văn A",
    "phone": "0912345678",
    "address": "Hà Nội",
    "shopping_preferences": ["điện thoại", "laptop"]
  },
  "conversation": {
    "messages": [
      {
        "role": "user",
        "content": "Tôi muốn tìm điện thoại Samsung",
        "timestamp": "2023-08-15T14:30:45.123Z"
      },
      {
        "role": "assistant",
        "content": "Tôi có thể giúp bạn tìm điện thoại Samsung. Bạn quan tâm đến model nào?",
        "timestamp": "2023-08-15T14:30:47.456Z"
      }
    ],
    "message_count": 2
  },
  "timestamp": "2023-08-15T14:35:22.789Z"
}
```

### Thiết lập instruction cho phiên chat

```
POST /api/set-instruction
```

#### Parameters

| Tham số | Kiểu | Bắt buộc | Mặc định | Mô tả |
|---------|------|----------|----------|-------|
| user_id | string | Có | - | ID của người dùng |
| session_id | string | Có | - | ID của phiên chat |
| instruction | string | Có | - | Instruction để áp dụng cho phiên chat |

**Request Example:**
```json
{
  "user_id": "user-123",
  "session_id": "session-456",
  "instruction": "Hãy trả lời ngắn gọn và luôn gợi ý cho tôi 3 sản phẩm liên quan"
}
```

**Response Example:**
```json
{
  "success": true,
  "message": "Đã cập nhật instruction cho phiên chat",
  "data": {
    "user_id": "user-123",
    "session_id": "session-456",
    "instruction": "Hãy trả lời ngắn gọn và luôn gợi ý cho tôi 3 sản phẩm liên quan",
    "applied": true
  }
}
```

## Mô hình dữ liệu

### UserProfile

Đối tượng lưu trữ thông tin người dùng:

```json
{
  "name": "Nguyễn Văn A",
  "phone": "0912345678",
  "address": "Hà Nội",
  "shopping_preferences": ["điện thoại", "laptop"],
  "viewed_products": ["Samsung Galaxy S23", "iPhone 15"],
  "cart_items": [
    {
      "id": "prod-123",
      "name": "Samsung Galaxy S23",
      "quantity": 1,
      "price": 19990000
    }
  ],
  "purchased_products": ["Samsung Galaxy Tab S9"],
  "last_query_topic": "product_search"
}
```

### Cơ chế quản lý context

Hệ thống quản lý context theo các nguyên tắc sau:

1. **Giới hạn lịch sử tin nhắn**: Số lượng tin nhắn tối đa được lưu trong context được kiểm soát bởi tham số `max_context_messages` (mặc định: 20 lượt trao đổi).

2. **Trích xuất thông tin người dùng**: Hệ thống tự động trích xuất thông tin từ tin nhắn của người dùng, bao gồm:
   - Tên
   - Số điện thoại
   - Địa chỉ
   - Sở thích mua sắm

3. **Cập nhật context động**: Context được cập nhật liên tục dựa trên:
   - Thông tin cá nhân người dùng
   - Sản phẩm đã xem gần đây
   - Giỏ hàng hiện tại

4. **Quản lý phiên**: Phiên chat có thể được reset để bắt đầu cuộc hội thoại mới, đồng thời giữ lại thông tin cá nhân người dùng.

5. **In-memory data**: Hệ thống lưu trữ dữ liệu in-memory để duy trì ngữ cảnh của cuộc hội thoại, bao gồm:
   - Thông tin phiên
   - Thông tin người dùng
   - Lịch sử hội thoại đã tóm tắt
   - Các instruction tùy chỉnh

## Ví dụ sử dụng

### JavaScript

```javascript
// Gửi tin nhắn thông thường
async function sendMessage(message) {
  const response = await fetch('http://localhost:5000/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: 'user-123',
      session_id: 'session-456',
      message: message,
      include_session_data: true,
      response_format: 'json'
    }),
  });
  
  const result = await response.json();
  
  // Xử lý kết quả dựa vào action
  switch(result.action) {
    case 'text':
      console.log('Phản hồi văn bản:', result.data.response);
      break;
    case 'search_products':
      console.log('Danh sách sản phẩm:', result.data.products);
      displayProductList(result.data.products);
      break;
    case 'get_product_detail':
      console.log('Chi tiết sản phẩm:', result.data.product);
      displayProductDetail(result.data.product);
      break;
    case 'add_to_cart':
      console.log('Đã thêm vào giỏ hàng:', result.data.product);
      updateCart(result.data.cart);
      break;
    case 'view_cart':
      console.log('Giỏ hàng:', result.data.cart);
      displayCart(result.data.cart);
      break;
    case 'place_order':
      console.log('Đơn hàng:', result.data.order);
      displayOrderConfirmation(result.data.order);
      break;
    case 'error':
      console.error('Lỗi:', result.data.error_message);
      displayError(result.data.error_message);
      break;
    default:
      console.log('Phản hồi không xác định:', result);
  }
  
  return result;
}

// Gửi tin nhắn stream (SSE)
function sendMessageWithStream(message) {
  const eventSource = new EventSource(
    `http://localhost:5000/api/chat/stream?message=${encodeURIComponent(message)}&user_id=user-123&session_id=session-456&response_format=json`
  );
  
  let fullContent = '';
  let action = 'text';
  
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    fullContent += data.content;
    
    if (data.action) {
      action = data.action;
    }
    
    // Hiển thị nội dung streaming
    if (action === 'text') {
      updateStreamingText(fullContent);
    }
    
    // Khi đã hoàn thành
    if (data.done) {
      eventSource.close();
      
      // Xử lý khi hoàn thành stream
      if (action === 'text') {
        console.log('Phản hồi văn bản hoàn chỉnh:', fullContent);
      } else {
        try {
          // Nếu nội dung bắt đầu bằng "json" thì loại bỏ prefix
          if (fullContent.startsWith('json\n')) {
            fullContent = fullContent.substring(5);
          }
          
          // Parse JSON từ chuỗi
          const jsonData = JSON.parse(fullContent);
          
          // Xử lý dữ liệu dựa vào action
          switch(action) {
            case 'search_products':
              console.log('Danh sách sản phẩm:', jsonData.products);
              displayProductList(jsonData.products);
              break;
            case 'get_product_detail':
              console.log('Chi tiết sản phẩm:', jsonData.product);
              displayProductDetail(jsonData.product);
              break;
            case 'add_to_cart':
              console.log('Đã thêm vào giỏ hàng:', jsonData.product);
              updateCart(jsonData.cart);
              break;
            case 'view_cart':
              console.log('Giỏ hàng:', jsonData.cart);
              displayCart(jsonData.cart);
              break;
            // Xử lý các action khác...
          }
        } catch (error) {
          console.error('Lỗi khi parse JSON:', error);
        }
      }
    }
  };
  
  eventSource.onerror = (error) => {
    console.error('Lỗi kết nối stream:', error);
    eventSource.close();
  };
}

// Sử dụng WebSocket
function connectWebSocket(userId, sessionId) {
  const ws = new WebSocket(`ws://localhost:5000/ws/${sessionId}`);
  let fullContent = '';
  let action = 'text';
  
  ws.onopen = () => {
    console.log('Kết nối WebSocket đã mở');
  };
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Nhận dữ liệu:', data);
    
    // Nếu tin nhắn có nội dung
    if (data.content) {
      fullContent += data.content;
      
      if (data.action) {
        action = data.action;
      }
      
      // Hiển thị nội dung streaming
      if (action === 'text') {
        updateStreamingText(fullContent);
      }
      
      // Xử lý khi hoàn thành lượt trả lời
      if (data.turn_complete) {
        if (action === 'text') {
          console.log('Phản hồi văn bản hoàn chỉnh:', fullContent);
          fullContent = '';
        } else {
          try {
            // Nếu nội dung bắt đầu bằng "json" thì loại bỏ prefix
            if (fullContent.startsWith('json\n')) {
              fullContent = fullContent.substring(5);
            }
            
            // Parse JSON từ chuỗi
            const jsonData = JSON.parse(fullContent);
            
            // Xử lý dữ liệu dựa vào action
            switch(action) {
              case 'search_products':
                console.log('Danh sách sản phẩm:', jsonData.products);
                displayProductList(jsonData.products);
                break;
              case 'get_product_detail':
                console.log('Chi tiết sản phẩm:', jsonData.product);
                displayProductDetail(jsonData.product);
                break;
              // Xử lý các action khác...
            }
            
            fullContent = '';
          } catch (error) {
            console.error('Lỗi khi parse JSON:', error);
          }
        }
      }
    }
  };
  
  ws.onclose = () => {
    console.log('Kết nối WebSocket đã đóng');
  };
  
  ws.onerror = (error) => {
    console.error('Lỗi WebSocket:', error);
  };
  
  // Gửi tin nhắn qua WebSocket
  function sendMessage(message, instruction = null) {
    if (ws.readyState === WebSocket.OPEN) {
      const payload = {
        message: message,
        user_id: userId
      };
      
      if (instruction) {
        payload.instruction = instruction;
      }
      
      ws.send(JSON.stringify(payload));
    } else {
      console.error('WebSocket chưa sẵn sàng');
    }
  }
  
  return {
    sendMessage,
    close: () => ws.close()
  };
}

// Các hàm hiển thị UI
function displayProductList(products) {
  // Hiển thị danh sách sản phẩm trong UI
}

function displayProductDetail(product) {
  // Hiển thị chi tiết sản phẩm trong UI
}

function updateCart(cart) {
  // Cập nhật UI giỏ hàng
}

function displayCart(cart) {
  // Hiển thị giỏ hàng trong UI
}

function displayOrderConfirmation(order) {
  // Hiển thị xác nhận đơn hàng trong UI
}

function displayError(message) {
  // Hiển thị thông báo lỗi trong UI
}

function updateStreamingText(text) {
  // Cập nhật UI với văn bản đang stream
}

// Tạo phiên mới
async function createNewSession(userId) {
  const response = await fetch(`http://localhost:5000/api/reset-session?user_id=${userId}&keep_profile=true`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  
  return await response.json();
}

// Lấy dữ liệu in-memory
async function getSessionMemory(userId, sessionId) {
  const response = await fetch(
    `http://localhost:5000/api/session-memory?user_id=${encodeURIComponent(userId)}&session_id=${encodeURIComponent(sessionId)}`
  );
  
  return await response.json();
}

// Thiết lập instruction cho phiên chat
async function setInstruction(userId, sessionId, instruction) {
  const response = await fetch('http://localhost:5000/api/set-instruction', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: userId,
      session_id: sessionId,
      instruction: instruction
    }),
  });
  
  return await response.json();
}
```

## Troubleshooting

- Nếu endpoint không trả về phản hồi, hãy kiểm tra xem server backend có đang chạy không (port 5000)
- Nếu phản hồi trả về lỗi "GOOGLE_API_KEY không được cấu hình", hãy kiểm tra biến môi trường
- Đối với stream API, một số trình duyệt cũ có thể không hỗ trợ Server-Sent Events, hãy sử dụng polyfill hoặc endpoint không stream
- Khi sử dụng WebSocket, đảm bảo xử lý đúng các trạng thái kết nối (onopen, onclose, onerror)
- Khi nhận dữ liệu JSON streaming, lưu ý cần đợi đến khi nhận đủ dữ liệu (done=true) trước khi parse
- Nếu gặp lỗi "WebSocket connection failed", hãy kiểm tra xem backend có hỗ trợ WebSocket không và cổng đã được mở đúng chưa
- Khi gặp lỗi parse JSON trong streaming, hãy kiểm tra xem đã nhận đủ dữ liệu chưa và định dạng JSON có đúng không
- Với SSE, một số proxy server có thể ngắt kết nối sau một khoảng thời gian không hoạt động, hãy xem xét việc sử dụng heartbeat để giữ kết nối
- Nếu nhận được JSON không đúng định dạng, kiểm tra xem có cần loại bỏ prefix 'json\n' không
- Với WebSocket, nếu kết nối bị đóng bất ngờ, triển khai cơ chế tự động kết nối lại sau một khoảng thời gian ngắn 