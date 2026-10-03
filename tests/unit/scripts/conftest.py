"""scripts の単体テストの共通 fixture（ワークスペースの fixture は tests/workspace_fixtures.py）。"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from fixture_types import FailingReplace, FailingUnlink, FailingWriteText, PatchPluginVersion

# このファイルから見たリポジトリの直下（tests/unit/scripts の 3 つ上）
REPO_ROOT_PARENT_DEPTH = 3
SCRIPTS_DIR = (
    Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]
    / "plugins"
    / "mindstella"
    / "skills"
    / "mindmap"
    / "scripts"
)

# スクリプトはパッケージとして入れず、同じフォルダの名前（import store など）で読む
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def scripts_dir() -> Path:
    """スクリプトのフォルダ（plugins/mindstella/skills/mindmap/scripts）を返す。"""
    return SCRIPTS_DIR


@pytest.fixture
def patch_plugin_version(monkeypatch: pytest.MonkeyPatch) -> PatchPluginVersion:
    """read_plugin_version を、渡した版を返す関数に差し替える関数を返す。"""

    def _install(text: str) -> None:
        """版の解釈・移し替えのモジュールが持つ read_plugin_version を、text の版を返すものに差し替える。"""
        # 移し替えのモジュールを読み込めない間も、他のテストの収集を止めないよう、使うときに読む
        import migrator
        import versions

        version = versions.parse_release_version(text)

        def _read_plugin_version(*args: Any, **kwargs: Any) -> Any:
            """プラグインの版のファイルを読まずに、決めた版を返す。"""
            return version

        # 版のモジュールの関数と、移し替えのモジュールが名前で取り込んだ関数の両方を差し替える
        monkeypatch.setattr(versions, "read_plugin_version", _read_plugin_version)
        monkeypatch.setattr(migrator, "read_plugin_version", _read_plugin_version, raising=False)

    return _install


@pytest.fixture
def failing_replace() -> FailingReplace:
    """指定したファイル名への置き換えだけを OSError にする os.replace の代わりを作る関数を返す。"""
    # monkeypatch で差し替える前の本物を控える
    real_replace = os.replace

    def _build(target_name: str) -> Callable[[Any, Any], None]:
        """置き換え先が target_name のときだけ失敗する関数を返す。"""

        def _replace(src: Any, dst: Any) -> None:
            """置き換え先の名前を見て、失敗させるか本物に任せるかを決める。"""
            # 失敗させる対象のファイルへの置き換え
            if Path(dst).name == target_name:
                raise OSError("置き換えできません")
            # それ以外は本物で置き換える
            real_replace(src, dst)

        return _replace

    return _build


@pytest.fixture
def failing_write_text(monkeypatch: pytest.MonkeyPatch) -> FailingWriteText:
    """指定したファイル名への Path.write_text だけを OSError にする関数を返す。"""
    # monkeypatch で差し替える前の本物を控える
    real_write_text = Path.write_text

    def _install(target_name: str) -> None:
        """Path.write_text を、target_name のときだけ失敗するものに差し替える。"""

        def _write_text(self: Path, data: str, *args: Any, **kwargs: Any) -> int:
            """書く先の名前を見て、失敗させるか本物に任せるかを決める。"""
            # 失敗させる対象のファイルへの書き込み
            if self.name == target_name:
                raise OSError("書き込めません")
            # それ以外は本物で書く
            return real_write_text(self, data, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", _write_text)

    return _install


@pytest.fixture
def failing_unlink(monkeypatch: pytest.MonkeyPatch) -> FailingUnlink:
    """指定したファイル名への Path.unlink だけを PermissionError にする関数を返す。"""
    # monkeypatch で差し替える前の本物を控える
    real_unlink = Path.unlink

    def _install(target_name: str) -> None:
        """Path.unlink を、target_name のときだけ失敗するものに差し替える。"""

        def _unlink(self: Path, *args: Any, **kwargs: Any) -> None:
            """消す先の名前を見て、失敗させるか本物に任せるかを決める。"""
            # 失敗させる対象のファイルを消すとき
            if self.name == target_name:
                raise PermissionError(13, "権限がありません")
            # それ以外は本物で消す
            real_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", _unlink)

    return _install
