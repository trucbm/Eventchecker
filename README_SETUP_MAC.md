# EventInspector Setup on macOS

File nay danh rieng cho may macOS.


## 1. Yeu cau toi thieu

Can co:

- Git
- Python 3.11 hoac 3.12
- Xcode Command Line Tools

Neu test Android:

- Android SDK
- `adb`

Neu test iOS:

- macOS
- bo tool doc log iOS ma team dang dung


## 2. Kiem tra cong cu san co

```bash
git --version
python3 --version
xcode-select -p
```

Neu co Android:

```bash
adb devices
```


## 3. Clone repo

```bash
git clone https://github.com/trucbm/Eventchecker.git
cd Eventchecker
```


## 4. Tao virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```


## 5. Chay local

```bash
python desktop_app.py
```

Neu app khong tim thay `adb`:

```bash
export ADB_PATH="$HOME/Library/Android/sdk/platform-tools/adb"
python desktop_app.py
```


## 6. Build macOS app

```bash
bash build/macos/build_macos.sh
```

Output:

- `dist/EventInspector.app`
- `dist/EventInspector.dmg`


## 7. Thu muc local state tren macOS

App state nam o:

```bash
~/Library/Application\ Support/EventInspector
```

Co the kiem tra:

```bash
ls -la "$HOME/Library/Application Support/EventInspector"
```


## 8. Neu update bi ket

Co the clear state local bang tay:

```bash
rm -f "$HOME/Library/Application Support/EventInspector/update_state_v230.json"
rm -f "$HOME/Library/Application Support/EventInspector/update_state_v240.json"
rm -f "$HOME/Library/Application Support/EventInspector/remote_update_config_v230.json"
rm -f "$HOME/Library/Application Support/EventInspector/remote_update_config_v240.json"
rm -rf "$HOME/Library/Application Support/EventInspector/updates_v230"
rm -rf "$HOME/Library/Application Support/EventInspector/updates_v240"
rm -rf "$HOME/Library/Application Support/EventInspector/updates_v230_tmp"
```


## 9. Quy trinh dev tren macOS

```bash
git checkout main
git pull origin main
git checkout -b feature/<ten-task>
```

Sau khi sua:

```bash
python desktop_app.py

# neu can test package
# bash build/macos/build_macos.sh

# khi moi thu OK thi moi push
git add <file>
git commit -m "Mo ta thay doi"
git push origin feature/<ten-task>
```

Flow khuyen nghi tren macOS:

1. Keo code moi nhat
2. Tao branch rieng
3. Sua code local
4. Chay `python desktop_app.py`
5. Neu thay doi lien quan package/update thi build local
6. Neu test OK moi commit/push
