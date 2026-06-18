# Meta Quest APK 빌드 가이드 — CPoW XR

Godot 4.6 + OpenXR로 **Meta Quest 2/3** APK를 빌드하는 절차입니다.

## 사전 준비

| 항목 | 버전·비고 |
|------|-----------|
| Godot | 4.6+ |
| Android export templates | Godot 에디터 → Editor → Manage Export Templates |
| Android SDK | API 33+, Android Studio SDK Manager |
| Android NDK | r23+ (Godot Export → Android → NDK Path) |
| JDK | 17 |
| Meta Quest | Developer Mode + USB 디버깅 |

### Godot 에디터 1회 설정

1. **Editor → Editor Settings → Export → Android**
   - Android SDK Path
   - Android NDK Path
   - Debug Keystore (자동 생성 가능)

2. **Project → Export**
   - `export_presets.quest.cfg` → `export_presets.cfg` 복사
   - 또는 `bash scripts/build_quest_apk.sh` (자동 복사)

3. **Export Preset "Meta Quest"** 확인
   - XR Mode: **OpenXR**
   - Hand Tracking: **On**
   - Architectures: **arm64-v8a** only
   - Min SDK: **29**
   - Internet permission: **On**
   - Package: `com.cpow.eldoria`

## 빌드

```bash
cd fantasy_simulator/client/godot

# export_presets.cfg 생성 (최초 1회)
cp export_presets.quest.cfg export_presets.cfg

# CLI 빌드 (Godot 경로 지정)
GODOT_BIN=/path/to/godot bash scripts/build_quest_apk.sh

# 출력: build/cpow-quest.apk
```

Godot 에디터에서: **Project → Export → Meta Quest → Export Project**

## Quest에 설치

1. Quest 헤드셋: **설정 → 시스템 → 개발자** → USB 연결 대화상자 허용
2. PC에 Meta Quest Developer Hub 또는 `adb` 설치
3. USB-C 연결 후:

```bash
adb devices
adb install -r build/cpow-quest.apk
```

앱 목록에서 **「CPoW XR」** 실행.

## API 서버 연결 (필수)

Quest는 `127.0.0.1`이 헤드셋 자신이므로, **개발 PC의 LAN IP**로 Python API에 접속해야 합니다.

### 1. PC에서 API 서버 (LAN 바인딩)

```bash
cd fantasy_simulator
pip install -r requirements-api.txt
uvicorn api.server:app --host 0.0.0.0 --port 8765
```

PC IP 확인: `ip addr` / `ifconfig` (예: `192.168.1.100`)

### 2. Quest에 API URL 설정

**방법 A — 앱 데이터 파일 (권장)**

`quest_api_url.txt.example`을 수정 후:

```bash
# 내용: http://192.168.1.100:8765
adb shell run-as com.cpow.eldoria sh -c \
  'echo "http://192.168.1.100:8765" > /data/data/com.cpow.eldoria/files/api_url.txt'
```

**방법 B — 빌드 시 상수 수정**

`scripts/net/api_config.gd`의 `QUEST_DEFAULT_LAN_API` 변경 후 재빌드.

**방법 C — 환경 변수 (에뮬레이터)**

`ELDORIA_API_URL=http://10.0.2.2:8765`

### 3. 방화벽

PC 방화벽에서 **8765/tcp** 인바운드 허용 (같은 Wi-Fi 대역).

## Quest 실행 흐름

1. Android 부팅 시 **자동으로 `world_xr.tscn`** 진입 (메뉴 생략)
2. OpenXR 초기화 → 컨트롤러 **트리거**로 창조
3. `POST /v1/xr/creation` → CPoW 엔진 → 3D 열원/재료 표시

## 조작 (Quest)

| 입력 | 동작 |
|------|------|
| **손 핀치 → 놓기** | 창조 (강도 = 핀치 세기) |
| **양손 핀치** | 오브젝트 연결 |
| **트리거** | 폴백 창조 |
| **스틱** | 이동 (향후) |

→ 상세: [XR_HAND_PINCH.md](XR_HAND_PINCH.md)

## 문제 해결

| 증상 | 해결 |
|------|------|
| OpenXR 초기화 실패 | Quest OS 업데이트, 앱 재설치 |
| API 연결 실패 | LAN IP·방화벽·`0.0.0.0` 바인딩 확인 |
| 검은 화면 | Export Preset에서 XR Mode=OpenXR 확인 |
| `export_presets.cfg` 없음 | `cp export_presets.quest.cfg export_presets.cfg` |
| SDK not found | Godot Editor Settings → Android SDK/NDK 경로 |

## 체크리스트

- [ ] Android export templates 설치
- [ ] SDK/NDK/JDK 경로 설정
- [ ] `export_presets.cfg` 생성
- [ ] APK 빌드 성공
- [ ] `adb install` 성공
- [ ] PC API `0.0.0.0:8765` 실행
- [ ] Quest에서 API URL 설정
- [ ] 트리거로 열원 창조 확인

## 관련 문서

- [XR_SETUP.md](XR_SETUP.md) — OpenXR 씬 구조
- [../../../../docs/XR_INTEGRATION.md](../../../../docs/XR_INTEGRATION.md) — CPoW XR 아키텍처
