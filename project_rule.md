# Quy tắc dự án: Chatbot MM A2A
Mã code backend tại C:\Users\HuyThanh\Desktop\mm_a2a, file chạy tạo server Uvicorn Fast API tại backend_server.py, file interface tại interface.md
Mã code Frontend tại C:\Users\HuyThanh\Desktop\mm-front-ts

## Quy tắc fix lỗi
Khi gặp lỗi 
-Nếu là lỗi cũ hoặc user yêu cầu thì mở lại task cũ để cập nhật trên đó 
- Nếu là lỗi mới và user không yêu cầu mở lại task cũ thì, hãy tạo task để fix lỗi, cập nhật vào task đang có lỗi dạng như task 01-fixbug yyyymmddhhss
- liệt kê các vấn đề như user đưa ra sau khi summarize và giải pháp của bạn. 
- cập nhật các task như hướng dẫn vào C:\Users\HuyThanh\Desktop\mm_a2a\tasklog.md
- Tắt hết các process đang chạy ở port 8000(frontend) và 5000 (backend)
- Sau khi kill các process khởi động lại các server ( backend tại C:\Users\HuyThanh\Desktop\mm_a2a\backend_server.py) , frontend tại C:\Users\HuyThanh\Desktop\mm-front-ts 
- Đảm bảo tất cả các vấn đề về khởi động xong và chờ user vào test
-khi user test xong mới cập nhật trạng thái fix bug này  

## Quy tắc chung cho Python
### Tổ chức code
- Tổ chức imports theo thứ tự: thư viện chuẩn, thư viện bên thứ ba, module nội bộ
- Sử dụng context managers (`with`) cho quản lý tài nguyên
- Xử lý ngoại lệ một cách rõ ràng và cụ thể
- Tránh các hàm quá dài (> 50 dòng) hoặc quá phức tạp

### Hiệu suất và bảo mật
- Tránh truy vấn cơ sở dữ liệu trong vòng lặp
- Sử dụng list comprehensions thay vì vòng lặp khi có thể
- Kiểm tra và validate đầu vào, đặc biệt là dữ liệu từ người dùng
- Không hiển thị thông tin nhạy cảm trong logs

## Quy tắc chung cho JavaScript/React

### Phong cách code
- Sử dụng ES6+ syntax khi có thể
- Ưu tiên sử dụng const và let thay vì var
- Sử dụng arrow functions cho các hàm callback
- Đặt tên biến, hàm theo quy ước camelCase
- Sử dụng destructuring để truy cập thuộc tính đối tượng

### React components
- Ưu tiên functional components với hooks thay vì class components
- Tách biệt UI và logic với custom hooks
- Sử dụng PropTypes hoặc TypeScript để kiểm tra kiểu dữ liệu props
- Tránh re-render không cần thiết với useMemo và useCallback
- Sử dụng key hợp lý khi render danh sách

### Quản lý state
- Sử dụng context API cho state toàn cục
- Tránh prop drilling (truyền props qua nhiều cấp component)
- Chia nhỏ state thành các phần hợp lý và có liên quan
- Xử lý side effects trong useEffect đúng cách

## Quy tắc dự án MM A2A

### 01. Tận dụng tính năng sẵn có
- **PHẢI** sử dụng tối đa các tính năng sẵn có của Google ADK và các framework hiện có
- **PHẢI** đọc kỹ tài liệu API của Google ADK trước khi triển khai bất kỳ tính năng nào
- **PHẢI** tận dụng các hàm và công cụ có sẵn trong mm_a2a/tools và các module liên quan
- **NÊN** tham khảo mã nguồn hiện có để hiểu cách các tính năng đã được triển khai
- **TRÁNH** xây dựng lại các chức năng đã tồn tại trong framework

### 02. Quy trình xây dựng tính năng mới
- **PHẢI** thông báo và xin xác nhận trước khi xây dựng bất kỳ tính năng nào từ đầu
- **PHẢI** cung cấp lý do rõ ràng tại sao cần xây dựng tính năng mới thay vì sử dụng tính năng có sẵn
- **PHẢI** đưa ra thiết kế chi tiết và ước tính thời gian trước khi bắt đầu
- **NÊN** bắt đầu với MVP (Minimal Viable Product) cho tính năng mới
- **TRÁNH** giả định về yêu cầu mà không xác nhận

### 03. Quy định về dữ liệu và mã giả
- **KHÔNG ĐƯỢC** sử dụng mock data trong các môi trường 
- **KHÔNG ĐƯỢC** sử dụng mock function trong trong các môi trường
- **PHẢI** sử dụng dữ liệu thật hoặc tương tác thực tế với API
- **PHẢI** xử lý các trường hợp lỗi và timeout trong tương tác API
- **NÊN** triển khai logging đầy đủ cho tất cả các tương tác API và xử lý lỗi

## Quy trình làm việc

### Quản lý mã nguồn
- Commit code thường xuyên với message rõ ràng
- Review code trước khi merge vào nhánh chính
- Viết unit test cho các chức năng quan trọng
- Cập nhật tài liệu khi có thay đổi lớn

### Kiểm tra chất lượng
- Chạy linting và formatting trước khi commit
- Kiểm tra code để tránh memory leaks
- Tối ưu hóa hiệu suất cho các component và hàm hay sử dụng
- Đảm bảo khả năng đọc và bảo trì code

### Giao tiếp và báo cáo
- Cập nhật tasklog.md với tiến độ công việc
- Báo cáo vấn đề kỹ thuật ngay khi phát hiện
- Ghi chú rõ ràng về các quyết định thiết kế quan trọng
- Cung cấp hướng dẫn sử dụng cho các tính năng mới

## Cập nhật và sửa đổi

Tài liệu này có thể được cập nhật theo thời gian dựa trên phản hồi từ nhóm phát triển và yêu cầu dự án. Mọi sửa đổi sẽ được ghi nhận và thông báo cho toàn bộ nhóm. 