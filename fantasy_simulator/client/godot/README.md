# Eldoria — Godot 4.6+ 클라이언트 (Steam)

이 폴더는 **완성된 Godot 프로젝트**입니다. Cursor와 Godot 에디터 모두에서 열 수 있습니다.

## 빠른 시작

1. **API 서버** (다른 터미널):

```bash
cd fantasy_simulator
pip install -r requirements-api.txt
uvicorn api.server:app --reload --port 8765
```

2. **Godot 4.6+** → Import → 이 폴더의 `project.godot` → F5

3. **Cursor** → 레포 루트 또는 이 폴더 열기 → [docs/CURSOR_GODOT.md](../../docs/CURSOR_GODOT.md)

## 구조

```
client/godot/
  project.godot          # config/features 4.6
  scenes/main_menu.tscn  # MVP UI + API 테스트
  scripts/net/
    api_config.gd        # Autoload
    api_client.gd        # Autoload — /v1/turn
```

## Cursor 연동

- 확장: **Godot Tools** (`geequlim.godot-tools`)
- `.vscode/settings.json` 에 `godot_tools.editor_path` 설정
- GDScript는 Cursor에서 편집, 씬·노드는 Godot 에디터에서 편집

## Steam

[docs/STEAM_GODOT.md](../../docs/STEAM_GODOT.md)
