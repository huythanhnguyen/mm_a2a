@echo off
echo === MM A2A Ecommerce Chatbot Backend Server ===
echo Khoi dong API Server tren port 5000

:: Khởi tạo biến môi trường nếu cần
if not defined GOOGLE_API_KEY (
    if exist .env (
        echo Dang tai bien moi truong tu file .env...
        for /F "tokens=*" %%A in (.env) do set %%A
    )
)

:: Kiểm tra API key
if not defined GOOGLE_API_KEY (
    echo LOI: Khong tim thay GOOGLE_API_KEY trong bien moi truong.
    echo Vui long dat GOOGLE_API_KEY trong file .env hoac bien moi truong he thong.
    exit /b 1
)

:: Khởi động server
echo Dang khoi dong backend server voi uvicorn...
python backend_server.py

echo Nhan phim bat ky de thoat...
pause > nul 