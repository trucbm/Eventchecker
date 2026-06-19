# EventInspector Team Setup Guide

Muc tieu cua file nay:
- Dua source code sang may moi de tiep tuc phat trien.
- Cho 2-3 nguoi co the cung lam viec tren cung 1 repo.
- Dam bao Codex tren may khac mo repo len la co the setup va tiep tuc lam chung.


## 1. Tong quan repo

Repo GitHub hien tai:

- `https://github.com/trucbm/Eventchecker.git`

Nhanh chinh:

- `main`: source code chung, on dinh de team cung phat trien.
- `2.4.0`: nhanh release/update payload cho app 2.4.

Thanh phan chinh trong repo:

- `desktop_app.py`: entry point cho desktop app.
- `Log_checker.py`: backend + frontend HTML/JS chinh cua tool.
- `remote_update.py`: logic updater/cache update.
- `requirements.txt`: dependency Python.
- `build/macos/`: script build macOS.
- `build/windows/`: script build Windows.
- `tools/`: script ho tro reset/update local.
- `Updates_2_3/`, `Updates_2_4/`: payload update cho cac kenh app.


## 2. Yeu cau tren may moi

Can co san:

- Git
- Python 3.11 hoac 3.12
- Internet de clone repo va cai dependency

Neu can test Android:

- Android SDK + `adb`

Neu can test iOS:

- macOS
- `libimobiledevice` / `idevicesyslog` hoac bo tool iOS ma team dang dung

Neu can build Windows app:

- Windows
- Python
- Neu build installer thi can Inno Setup

Neu can build macOS app:

- macOS
- Python
- Xcode Command Line Tools


## 3. Clone repo ve may moi

```bash
git clone https://github.com/trucbm/Eventchecker.git
cd Eventchecker
```

Kiem tra nhanh:

```bash
git remote -v
git branch
```


## 4. Tao moi truong Python

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Windows CMD:

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```


## 5. Chay app local

Chay desktop app:

```bash
python desktop_app.py
```

Mac/Linux:
- App thuong mo local server tai `http://127.0.0.1:5001`
- Neu port `5001` dang ban, app se tu chon port khac

Neu muon chay backend truc tiep de debug:

```bash
python Log_checker.py
```

Neu may khong nhan Android device:

- kiem tra `adb devices`
- neu can, set bien moi truong `ADB_PATH`

Vi du macOS:

```bash
export ADB_PATH="$HOME/Library/Android/sdk/platform-tools/adb"
python desktop_app.py
```


## 6. Kiem tra dependency thiet bi

Android:

```bash
adb devices
```

iOS tren macOS:

- Neu team dung `idevicesyslog`, kiem tra tool do truoc
- Neu team dung `tidevice`, cai rieng tren may can test

Luu y:
- Repo nay khong tu dong cai bo tool iOS system-level
- Moi dev tu setup phan iOS test tren may cua minh


## 7. Cach lam viec nhieu nguoi

Khuyen nghi workflow:

- Khong code truc tiep tren `main`
- Moi task tao 1 branch rieng
- Xong thi push branch va merge lai

Buoc lam viec moi ngay:

```bash
git checkout main
git pull origin main
git checkout -b feature/ten-task
```

Sau khi sua:

```bash
git add .
git commit -m "Mo ta thay doi"
git push origin feature/ten-task
```

Sau do tao Pull Request tren GitHub.

Neu team chua dung PR nghiem tuc, van nen giu toi thieu quy tac:

- Moi nguoi 1 branch
- Merge xong moi quay lai `main`
- Luon `git pull origin main` truoc khi tao branch moi


## 8. Quy tac file nen va khong nen commit

Nen commit:

- `Log_checker.py`
- `desktop_app.py`
- `remote_update.py`
- `requirements.txt`
- file trong `build/`
- file trong `tools/`
- `Updates_2_3/`, `Updates_2_4/`
- cac file README/huong dan

Khong nen commit:

- `__pycache__/`
- `*.pyc`
- file build da dong goi
- `dist/EventInspector.dmg`
- `dist/EventInspector.app`
- `dist/EventInspector/`
- `.venv/`
- `.worktrees/`

Repo da co `.gitignore` cho phan lon cac file local/build.


## 9. Build app

### 9.1 Build macOS

```bash
bash build/macos/build_macos.sh
```

Output:

- `dist/EventInspector.app`
- `dist/EventInspector.dmg`


### 9.2 Build Windows portable

Chay tren Windows:

```bat
build\windows\build_portable.bat
```

Output:

- `dist\EventInspector\`


### 9.3 Build Windows installer

Doc them:

- `build/windows/README_INSTALLER_WINDOWS.md`


## 10. Remote update / payload update

App hien co co che update payload thong qua:

- `remote_update.py`
- `Updates_2_3/remote_manifest.json`
- `Updates_2_4/remote_manifest.json`

Khi sua mot tinh nang ma app can nhan qua updater:

1. Sua source chinh can thiet
2. Dong bo payload trong `Updates_2_3/` hoac `Updates_2_4/`
3. Tang version/badge neu can
4. Cap nhat `sha256` trong manifest
5. Commit va push

Neu chi sua source local de dev, khong nhat thiet phai publish updater ngay.


## 11. Cach tiep tuc bang Codex tren may khac

Neu mo repo nay bang Codex o may khac, lam nhu sau:

1. Clone repo
2. Cai Python + dependency
3. Mo Codex tai root repo nay
4. Bao Codex doc cac file sau truoc khi sua:
   - `README_SETUP_TEAM.md`
   - `README_APP.md`
   - `requirements.txt`
   - `desktop_app.py`
   - `Log_checker.py`

Neu Codex can biet cach van hanh team:

- Code tren branch rieng
- Khong commit file build/cache local
- Neu can publish update, sua dung manifest/payload

Luu y:

- Trong may hien tai co file AGENTS tham chieu toi file local:
  - `/Users/truc.bui/.codex/RTK.md`
- Tren may khac co the khong co duong dan nay
- Neu Codex o may moi bao thieu file huong dan local, chi can tiep tuc dua tren repo nay va file `README_SETUP_TEAM.md`


## 12. Neu dev moi muon lay ban moi nhat

```bash
git checkout main
git pull origin main
```

Neu dang o branch rieng:

```bash
git fetch origin
git merge origin/main
```

Hoac:

```bash
git rebase origin/main
```


## 13. Xu ly xung dot co ban

Neu Git bao conflict:

1. Mo file bi conflict
2. Tim cac doan:

```text
<<<<<<<
=======
>>>>>>>
```

3. Chon noi dung dung
4. Xoa marker conflict
5. Sau do:

```bash
git add <file>
git commit
```


## 14. Checkpoint / revert

Repo nay co the dung tag checkpoint de quay lai moc on dinh.

Xem tag:

```bash
git tag
```

Xem commit hien tai:

```bash
git rev-parse --short HEAD
```

Checkout tam 1 checkpoint:

```bash
git checkout <tag-name>
```

Tao branch moi tu checkpoint:

```bash
git checkout -b hotfix/from-checkpoint <tag-name>
```


## 15. Checklist setup nhanh cho may moi

1. Clone repo
2. Tao `.venv`
3. `pip install -r requirements.txt`
4. Kiem tra `adb` neu test Android
5. `python desktop_app.py`
6. Tao branch rieng truoc khi sua
7. Commit va push branch len GitHub


## 16. Neu co van de

Neu app khong chay:

- kiem tra da activate `.venv` chua
- kiem tra `pip install -r requirements.txt` da xong chua
- kiem tra port local co dang bi chiem khong
- kiem tra `adb` / tool iOS co san khong

Neu updater khong dung:

- kiem tra `remote_manifest.json`
- kiem tra `sha256`
- kiem tra branch `main` va `2.4.0` da push chua


## 17. Khuyen nghi cho team

De lam viec on dinh voi 2-3 nguoi:

- dung GitHub private repo
- moi task la 1 branch
- merge qua PR
- giu `main` sach va chay duoc
- ghi ro trong commit message la sua source local hay publish update payload

