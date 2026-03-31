# Windows Installer (1-click)

Mục tiêu: tạo file cài đặt `EventInspector-Setup.exe` để người dùng chỉ cần double-click và Install.

## Cách build (trên máy Windows)
1. Cài Python 3.10+ (tick "Add Python to PATH").
2. Cài Inno Setup (ISCC) và đảm bảo `ISCC.exe` có trong PATH.
3. Mở folder dự án rồi double-click file:
   `build\windows\build_windows.bat`

Kết quả:
- File installer sẽ nằm tại `Output` của Inno Setup (mặc định cùng thư mục `.iss`).
- Tên file: `EventInspector-Setup.exe`.

## Đóng gói kèm file params
- Nếu có file `Default event + Default Params.xlsx` ở root dự án, nó sẽ được copy vào thư mục cài đặt.
- Nếu muốn dùng file khác, set biến môi trường `DEFAULT_PARAMS_XLSX_PATH` trong Windows.
