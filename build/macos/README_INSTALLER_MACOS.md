# macOS App + DMG

Mục tiêu: tạo `EventInspector.app` và `EventInspector.dmg` để người dùng kéo thả cài đặt.

## Cách build (trên macOS)
```bash
bash build/macos/build_macos.sh
```

Build macOS mặc định dùng `universal2`, nên một file DMG chạy được trên cả
Mac Intel (`x86_64`) và Apple Silicon (`arm64`). Có thể kiểm tra binary sau
khi build bằng:

```bash
lipo -info dist/EventInspector.app/Contents/MacOS/EventInspector
```

Kết quả cần có cả `x86_64` và `arm64`.

Kết quả:
- `dist/EventInspector.app`
- `dist/EventInspector.dmg`

## Icon
Script sẽ tự tạo `assets/app.icns` từ PNG này nếu có:
`/Users/truc.bui/Downloads/82690-protective-slitherio-personal-wallpaper-equipment-computer-snake.png`

Nếu PNG nằm chỗ khác, chỉnh biến `PNG_SRC` trong `build/macos/build_macos.sh`.

## Default params file
- File `Default event + Default Params.xlsx` được đóng gói vào app.
- Bạn có thể chỉnh file trong `EventInspector.app/Contents/Resources/`.
- App sẽ ưu tiên đọc file ở thư mục app rồi mới fallback ra `~/Downloads` / `~/Documents`.

## ADB (nếu app không nhận device)
- App sẽ tự tìm `adb` trong PATH.
- Có thể set biến môi trường `ADB_PATH` (ví dụ `/opt/homebrew/bin/adb`).
