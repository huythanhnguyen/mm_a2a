# Product Requirements Document (PRD)
# MM A2A Ecommerce Chatbot

## Tổng quan dự án

### Mục đích
Xây dựng một chatbot thông minh có khả năng hỗ trợ khách hàng tìm kiếm và đặt hàng trên trang web ecommerce, sử dụng kiến trúc agent-to-agent (a2a) với Google ADK.

### Mô tả tổng quan
Chatbot sẽ hoạt động như một trợ lý ảo, hiểu được nhu cầu của khách hàng, giúp họ tìm kiếm sản phẩm, xem thông tin chi tiết và hoàn tất quá trình đặt hàng trên trang web ecommerce. Hệ thống được thiết kế với kiến trúc gồm một root agent quản lý tất cả các tương tác với người dùng và điều phối các sub-agent chuyên biệt để thực hiện các chức năng tìm kiếm, đặt hàng và đăng nhập.

### Đối tượng người dùng
- Khách hàng của trang web ecommerce MM Vietnam
- Khách hàng tiềm năng đang tìm hiểu sản phẩm
- Người dùng cần hỗ trợ trong quá trình mua sắm trực tuyến
- Người dùng có tài khoản MCard muốn tích hợp thông tin khi mua sắm

## Kiến trúc hệ thống

### Tổng quan kiến trúc
- **Frontend**: Giao diện người dùng để tương tác với chatbot
- **Backend**: Hệ thống xử lý yêu cầu từ người dùng, sử dụng kiến trúc a2a với Google ADK
  - **Root Agent**: Tiếp nhận và phân tích yêu cầu của người dùng, điều phối sub-agent
  - **CnG Agent**: Chịu trách nhiệm mọi nhiệm vụ liên quan đến tìm kiếm sản phẩm, đặt hàng, quản lý đơn hàng và xử lý đăng nhập trên trang Click and Get (https://online.mmvietnam.com/)

### Mô hình Sub-Agents
- **Root Agent**: Điều phối toàn bộ tương tác
- **CnG Agent**: Chịu trách nhiệm các nhiệm vụ liên quan đến tìm kiếm, đặt hàng và quản lý đơn hàng của trang Click and Get https://online.mmvietnam.com/
  - **Product Agent**: Tìm kiếm và hiển thị thông tin sản phẩm
  - **Cart Manager Agent**: Quản lý giỏ hàng và quy trình thanh toán
  - **Order Flow Agent**: Quản lý và theo dõi thông tin đơn hàng
    - **Order Details Agent**: Kiểm tra thông tin chi tiết đơn hàng
    - **Payment Details Agent**: Kiểm tra thông tin thanh toán
    - **Delivery Details Agent**: Kiểm tra thông tin giao hàng

### Công nghệ sử dụng
- **Ngôn ngữ lập trình**: Python (cho phần agent)
- **Framework AI**: Google ADK (Agent Development Kit) với Gemini 2.0 model
- **API Integration**: Kết nối với GraphQL API của MM Ecommerce
- **Bộ nhớ phiên**: Sử dụng State Management để lưu trữ thông tin người dùng, giỏ hàng, và lịch sử tìm kiếm
- **Xử lý bất đồng bộ**: async/await với aiohttp cho các cuộc gọi API

## Yêu cầu chức năng

### Root Agent
1. **Hiểu nhu cầu người dùng**
   - Phân tích ngữ cảnh và ý định từ tin nhắn của người dùng
   - Trích xuất thông tin quan trọng (sản phẩm quan tâm, tiêu chí tìm kiếm, ý định mua hàng)
   - Xác định khi nào cần chuyển yêu cầu đến sub-agent

2. **Điều phối tương tác**
   - Quản lý luồng hội thoại với người dùng
   - Chuyển yêu cầu phù hợp đến CnG agent
   - Tổng hợp kết quả từ CnG agent và trình bày cho người dùng một cách mạch lạc

3. **Xử lý hội thoại**
   - Duy trì ngữ cảnh hội thoại
   - Đảm bảo trải nghiệm người dùng liền mạch
   - Xử lý các câu hỏi phổ biến không liên quan đến tìm kiếm/đặt hàng

### CnG Agent (Click and Get)
1. **Tìm kiếm sản phẩm (Product Agent)**
   - Tìm kiếm sản phẩm dựa trên các tiêu chí (tên, danh mục, giá cả, tính năng)
   - Lọc và sắp xếp kết quả tìm kiếm
   - Hiển thị thông tin sản phẩm (hình ảnh, giá, mô tả, đánh giá)
   - Tìm kiếm sản phẩm theo article number (mm_art_no)
   - Lưu trữ lịch sử tìm kiếm của người dùng

2. **Quản lý giỏ hàng (Cart Manager Agent)**
   - Tạo giỏ hàng mới (cho khách đã đăng nhập hoặc chưa đăng nhập)
   - Thêm sản phẩm vào giỏ hàng
   - Cập nhật số lượng sản phẩm trong giỏ hàng
   - Xóa sản phẩm khỏi giỏ hàng
   - Xử lý quá trình thanh toán
   - Lưu trữ thông tin giỏ hàng

3. **Xử lý đăng nhập/đăng ký**
   - Hỗ trợ người dùng đăng nhập vào tài khoản
   - Xử lý đăng nhập thông qua MCard
   - Tạo tài khoản mới từ thông tin MCard (nếu cần)
   - Quản lý và làm mới token xác thực
   - Đảm bảo bảo mật thông tin người dùng

4. **Quản lý đơn hàng (Order Flow Agent)**
   - Điều phối quy trình kiểm tra và theo dõi đơn hàng
   - Tổng hợp thông tin từ các agent con
   - Lưu trữ thông tin đơn hàng trong phiên làm việc
   
   4.1 **Kiểm tra đơn hàng (Order Details Agent)**
   - Kiểm tra trạng thái đơn hàng
   - Cung cấp thông tin chi tiết về đơn hàng
   - Xử lý các vấn đề liên quan đến đơn hàng
   
   4.2 **Kiểm tra thanh toán (Payment Details Agent)**
   - Kiểm tra trạng thái thanh toán
   - Xác nhận phương thức thanh toán
   - Cung cấp thông tin hóa đơn
   
   4.3 **Kiểm tra giao hàng (Delivery Details Agent)**
   - Theo dõi quá trình giao hàng
   - Cung cấp thông tin về thời gian giao hàng dự kiến
   - Xử lý các vấn đề về giao hàng

5. **Hỗ trợ sau bán hàng**
   - Hỗ trợ đổi/trả hàng
   - Xử lý khiếu nại về đơn hàng
   - Cung cấp thông tin bảo hành

## Tích hợp API

### Endpoint GraphQL chính
- **URL**: https://online.mmvietnam.com/graphql

### API Endpoints

#### 1. API Tìm kiếm sản phẩm
- **Method**: GET (cho hiệu suất tốt hơn)
- **Header**:
  - Store: b2c_10010_vi (Trong đó b2c_ là tiền tố, 10010 là mã cửa hàng, _vi là hậu tố ngôn ngữ)
- **Chức năng**:
  - Tìm kiếm sản phẩm theo từ khóa
  - Tìm kiếm sản phẩm theo article number (mm_art_no)
  - Lọc sản phẩm theo nhiều tiêu chí
  - Phân trang kết quả

#### 2. API Chi tiết sản phẩm
- **Method**: GET
- **Header**: Store: b2c_10010_vi
- **Chức năng**:
  - Lấy thông tin chi tiết của sản phẩm theo SKU
  - Lấy thông tin giá, hình ảnh, mô tả, đơn vị sản phẩm

#### 3. API Đăng nhập
- **Method**: POST
- **Header**: Store: b2c_10010_vi
- **Chức năng**:
  - Đăng nhập thông thường với email/password
  - Trả về token xác thực

#### 4. API Đăng nhập MCard
- **Method**: POST
- **Header**: Store: b2c_10010_vi
- **Chức năng**:
  - Đăng nhập với thông tin MCard
  - Tạo tài khoản mới từ thông tin MCard (nếu chưa có)

#### 5. API Quản lý giỏ hàng
- **Method**: POST
- **Header**:
  - Store: b2c_10010_vi
  - Authorization: Bearer token (cho người dùng đã đăng nhập)
- **Chức năng**:
  - Tạo giỏ hàng mới (cho cả khách đăng nhập và chưa đăng nhập)
  - Thêm sản phẩm vào giỏ hàng
  - Cập nhật số lượng sản phẩm
  - Xóa sản phẩm khỏi giỏ hàng

#### 6. API Kiểm tra thời gian hết hạn token
- **Method**: GET
- **Header**: Store: b2c_10010_vi
- **Chức năng**:
  - Lấy thông tin về thời gian sống của token (đơn vị giờ)

### Quy trình sử dụng API

#### Tìm kiếm sản phẩm
1. Gửi GraphQL query với từ khóa tìm kiếm
2. Xử lý và hiển thị kết quả tìm kiếm
3. Hỗ trợ lọc và phân trang nếu cần

#### Thêm sản phẩm vào giỏ hàng
1. **Người dùng đã đăng nhập**:
   - Kiểm tra token xác thực
   - Tạo giỏ hàng thông qua mutation `createEmptyCart`
   - Thêm sản phẩm vào giỏ hàng thông qua mutation `addProductsToCart`

2. **Người dùng chưa đăng nhập**:
   - Tạo giỏ hàng khách thông qua mutation `createGuestCart`
   - Thêm sản phẩm vào giỏ hàng thông qua mutation `addProductsToCart`

#### Đăng nhập với MCard
1. Gọi API `generateLoginMcardInfo` với thông tin MCard
2. Xử lý kết quả:
   - Nếu `customer_token` không null: Đăng nhập thành công
   - Nếu `customer_token` là null: Chưa có tài khoản, cần tạo mới
   - Nếu có lỗi: Thông tin không chính xác
3. Nếu cần tạo tài khoản mới, gọi API `createCustomerFromMcard`

## Chi tiết kết quả thử nghiệm

### Tìm kiếm sản phẩm cá hồi
- Đã tìm thấy 10 sản phẩm cá hồi khác nhau
- Các loại sản phẩm bao gồm:
  - Xương cá hồi nhập khẩu (SKU: 159954_21599545) - 59,000đ
  - Vây cá hồi nhập khẩu đông lạnh (SKU: 206344_22063441) - 115,000đ
  - Đầu cá hồi tươi nhập khẩu (SKU: 159956_21599569) - 59,000đ
  - Cá hồi Chile fillet thăn tươi (SKU: 434249_24342490) - 499,000đ
  - Phi lê đuôi cá hồi Nauy tươi (SKU: 384332_23843325) - 419,000đ
  - Và các sản phẩm khác

### Thêm sản phẩm vào giỏ hàng
- Đã tạo giỏ hàng mới thành công với ID ngẫu nhiên
- Đã thêm thành công 2 sản phẩm vào giỏ hàng:
  - Sản phẩm 1: Xương cá hồi nhập khẩu (SKU: 159954_21599545)
  - Sản phẩm 2: Vây cá hồi nhập khẩu đông lạnh (SKU: 206344_22063441)
- Không gặp lỗi trong quá trình thêm vào giỏ hàng

## Luồng tương tác người dùng

### Kịch bản 1: Tìm kiếm sản phẩm
1. Người dùng gửi yêu cầu tìm kiếm sản phẩm (VD: "tìm sản phẩm cá hồi")
2. Root agent phân tích yêu cầu và chuyển đến CnG agent
3. Product agent (thuộc CnG) thực hiện tìm kiếm thông qua API GraphQL
4. Product agent xử lý kết quả và trả về danh sách sản phẩm
5. Root agent trình bày kết quả cho người dùng một cách rõ ràng
6. Người dùng có thể yêu cầu thông tin chi tiết hơn hoặc lọc kết quả

### Kịch bản 2: Đặt hàng
1. Người dùng chọn sản phẩm muốn đặt hàng
2. Root agent chuyển yêu cầu đến CnG agent
3. CnG agent kiểm tra trạng thái đăng nhập
   - Nếu chưa đăng nhập, tạo giỏ hàng khách (guest cart)
   - Nếu đã đăng nhập, tạo giỏ hàng người dùng (customer cart)
4. Cart Manager agent thêm sản phẩm vào giỏ hàng thông qua API
5. Root agent thông báo kết quả và hỏi người dùng có muốn thêm sản phẩm khác không
6. Khi người dùng muốn thanh toán, hệ thống sẽ hướng dẫn tiến hành thanh toán

### Kịch bản 3: Đăng nhập với MCard
1. Người dùng gửi yêu cầu đăng nhập với MCard
2. Root agent chuyển yêu cầu đến CnG agent
3. CnG agent gọi API `generateLoginMcardInfo` với thông tin MCard
4. Nếu `customer_token` có giá trị, đăng nhập thành công
5. Nếu `customer_token` là null, CnG agent tạo tài khoản mới bằng API `createCustomerFromMcard`
6. Root agent thông báo kết quả đăng nhập và hướng dẫn người dùng tiếp tục mua sắm

### Kịch bản 4: Theo dõi đơn hàng
1. Người dùng gửi yêu cầu kiểm tra trạng thái đơn hàng
2. Root agent chuyển yêu cầu đến CnG agent
3. Order Details Agent (thuộc CnG) kiểm tra thông tin đơn hàng
4. Payment Details Agent (thuộc CnG) kiểm tra thông tin thanh toán
5. Delivery Details Agent (thuộc CnG) kiểm tra thông tin giao hàng
6. CnG agent tổng hợp thông tin và trả về cho Root agent
7. Root agent trình bày thông tin đơn hàng đầy đủ cho người dùng

## Xử lý lỗi và tình huống đặc biệt

### Xử lý lỗi API
- Sử dụng thư viện tenacity để thử lại các cuộc gọi API bị lỗi (với giới hạn số lần thử lại)
- Xử lý các lỗi phổ biến như:
  - Sản phẩm không tồn tại: PRODUCT_NOT_FOUND
  - Lỗi xác thực: graphql-authentication
  - Lỗi timeout: Cung cấp thông báo phù hợp cho người dùng

### Quản lý phiên làm việc
- Lưu trữ thông tin phiên người dùng, bao gồm ID phiên và thời gian tạo
- Theo dõi thời gian sống của token xác thực và làm mới khi cần
- Lưu trữ lịch sử tìm kiếm và sản phẩm đã xem để cải thiện trải nghiệm

### Xử lý ngôn ngữ
- Hỗ trợ tiếng Việt và tiếng Anh thông qua header Store
- Xử lý các ký tự đặc biệt trong tiếng Việt khi hiển thị và tìm kiếm

## Yêu cầu phi chức năng

### Hiệu suất
- Thời gian phản hồi của chatbot < 2 giây
- Sử dụng method GET cho các API tìm kiếm để tối ưu hiệu suất
- Tối ưu việc gọi API để giảm thiểu độ trễ (caching, batching)

### Bảo mật
- Không lưu trữ mật khẩu người dùng
- Lưu trữ token an toàn và tự động hết hạn theo cấu hình
- Mã hóa dữ liệu trao đổi
- Tuân thủ các quy định về bảo vệ dữ liệu cá nhân

### Khả năng mở rộng
- Thiết kế cho phép thêm sub-agents mới trong tương lai
- Hỗ trợ tích hợp với nhiều cửa hàng MM Vietnam khác nhau
- Cấu trúc mô-đun cho phép cập nhật từng phần mà không ảnh hưởng đến toàn bộ hệ thống

### Độ tin cậy
- Xử lý lỗi API một cách mềm dẻo với thử lại tự động
- Ghi log đầy đủ cho mọi tương tác API để theo dõi và điều tra sự cố
- Đảm bảo tính nhất quán của dữ liệu giữa các phiên làm việc

## Kế hoạch triển khai

### Giai đoạn 1: Phát triển cơ bản
- Thiết lập cấu trúc dự án và các thành phần cốt lõi
- Triển khai root agent với khả năng hiểu cơ bản
- Triển khai CnG agent với chức năng tìm kiếm sản phẩm
- Tích hợp API tìm kiếm và chi tiết sản phẩm

### Giai đoạn 2: Mở rộng chức năng
- Cải thiện khả năng hiểu của root agent
- Thêm chức năng giỏ hàng và đặt hàng vào CnG agent
- Tích hợp xử lý đăng nhập thông thường và MCard
- Triển khai các sub-agent quản lý đơn hàng (Order Details, Payment Details, Delivery Details)

### Giai đoạn 3: Tối ưu và hoàn thiện
- Cải thiện trải nghiệm người dùng
- Tối ưu hiệu suất của hệ thống
- Mở rộng khả năng xử lý ngôn ngữ tự nhiên
- Tích hợp phân tích và báo cáo để cải thiện hiệu quả của chatbot

## Phụ lục

### Các thuật ngữ
- **a2a**: Agent-to-agent, kiến trúc sử dụng nhiều agent AI cùng phối hợp
- **Google ADK**: Agent Development Kit, bộ công cụ phát triển agent của Google
- **Root Agent**: Agent chính, điều phối các sub-agent
- **CnG Agent**: Click and Get Agent, sub-agent chịu trách nhiệm tìm kiếm, đặt hàng và quản lý đơn hàng trên trang Click and Get https://online.mmvietnam.com/
- **SKU**: Stock Keeping Unit, mã quản lý sản phẩm
- **mm_art_no**: Article Number, mã sản phẩm của MM Vietnam
- **MCard**: Hệ thống thẻ thành viên của MM Vietnam

### Tài liệu tham khảo
- "[MMVN x Magenest] API Doc for E-brochure.docx"
- Tài liệu về Google ADK
- Kết quả thử nghiệm với API MM Vietnam