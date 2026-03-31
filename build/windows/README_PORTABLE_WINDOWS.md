# Windows Portable (no installer)

Mục tiêu: tạo bản portable dạng folder, người dùng chỉ cần giải nén và chạy EXE.

## Build trên Windows
1) Chạy:
```
build\windows\build_portable.bat
```

2) Lấy thư mục output:
`dist\EventInspector\`

3) Zip thư mục này lại và gửi cho user.

User chỉ cần:
- Giải nén
- Chạy `EventInspector.exe`
- Có thể sửa file default ngay trong thư mục đó.
