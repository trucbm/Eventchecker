# Event Checker Desktop App

## 1) Chạy thử ở máy dev
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python desktop_app.py
```

## 2) Build app Windows (EXE)
```bash
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --icon assets/app.ico --name "EventInspector" \
  --hidden-import "engineio.async_drivers.threading" \
  --hidden-import "socketio.async_drivers.threading" \
  desktop_app.py
```
Kết quả ở `dist/EventInspector/EventInspector.exe`.

## 3) Build app macOS (.app)
```bash
bash build/macos/build_macos.sh
```
Kết quả ở `dist/EventInspector.app` và `dist/EventInspector.dmg`.

## 4) Tạo bộ cài (installer)
- Windows: dùng Inno Setup hoặc NSIS để tạo file cài đặt từ thư mục `dist/EventChecker/`.
- macOS: dùng `hdiutil` hoặc `create-dmg` để tạo `.dmg` từ `dist/EventChecker.app`.

## 5) File cấu hình mặc định params
- Khi build, file `Default event + Default Params.xlsx` sẽ được đóng gói vào app.
- Sau khi cài, bạn có thể chỉnh file ngay trong thư mục cài đặt của app.
- App sẽ ưu tiên đọc file ở:
  - Cùng thư mục với app (Windows) hoặc `Contents/Resources` (macOS)
  - `~/Downloads`, `~/Documents`
  - Hoặc set `DEFAULT_PARAMS_XLSX_PATH`

## 6) ADB path (nếu app không nhận device)
- App sẽ tự tìm `adb` trong PATH.
- Có thể set biến môi trường `ADB_PATH` để trỏ thẳng tới `adb` (ví dụ `/opt/homebrew/bin/adb`).
