from __future__ import annotations

import os
from unittest.mock import patch

from acorn.i18n import (
    _lookup,
    cmd_text,
    detect_language,
    error,
    get_language,
    load_translations,
    prompt,
    set_language,
    text,
)


def test_detect_language_default():
    lang = detect_language(None)
    assert lang in ("en", "zh")


def test_detect_language_args():
    lang = detect_language("zh")
    assert lang == "zh"


def test_set_language():
    set_language("en")
    assert text("detected", type="node", confidence="50%") == "Detected: node (confidence: 50%)"


def test_i18n_text_zh():
    set_language("zh")
    msg = text("detected", type="Node.js", confidence="80%")
    assert "检测到" in msg
    assert "Node.js" in msg


def test_i18n_text_missing_key():
    set_language("en")
    result = text("nonexistent_key_xyz")
    assert "nonexistent_key_xyz" in result


def test_i18n_error():
    set_language("en")
    msg = error("not_found", name="test")
    assert "Not found" in msg


def test_i18n_error_zh():
    set_language("zh")
    msg = error("dir_not_exist", dir="/foo")
    assert "目录不存在" in msg


def test_i18n_prompt():
    set_language("en")
    msg = prompt("confirm_template", name="node-api")
    assert "Use template" in msg


def test_i18n_cmd_text():
    set_language("en")
    msg = cmd_text("list_title", count="5")
    assert "5" in msg


def test_i18n_switch_languages():
    set_language("zh")
    zh_msg = text("not_detected")
    set_language("en")
    en_msg = text("not_detected")
    assert zh_msg != en_msg
    assert "无法检测" in zh_msg
    assert "Could not detect" in en_msg


def test_detect_language_env_var():
    with patch.dict(os.environ, {"INIT_PROJECT_LANG": "zh"}, clear=True):
        lang = detect_language(None)
        assert lang == "zh"


def test_detect_language_sys_lang():
    with patch.dict(os.environ, {"LANG": "zh_CN.UTF-8"}, clear=True):
        lang = detect_language(None)
        assert lang == "zh"


def test_detect_language_sys_lang_en():
    with patch.dict(os.environ, {"LANG": "en_US.UTF-8"}, clear=True):
        lang = detect_language(None)
        assert lang == "en"


def test_get_language():
    set_language("zh")
    assert get_language() == "zh"
    set_language("en")


def test_load_translations_missing():
    translations = load_translations("nonexistent")
    assert isinstance(translations, dict)
    assert len(translations) > 0  # falls back to en.yaml


def test_load_translations_no_en_fallback(tmp_path):
    with patch("acorn.i18n.LOCALES_DIR", tmp_path):
        translations = load_translations("en")
        assert translations == {}


def test_lookup_non_dict():
    from acorn.i18n import _lookup
    data = {"key": "value", "nested": {"inner": "ok"}}
    assert _lookup("nested.inner", data) == "ok"
    # accessing a key on a non-dict intermediate
    result = _lookup("key.sub", data)
    assert result is None


def test_lookup_non_string_leaf():
    from acorn.i18n import _lookup
    data = {"key": {"nested": {}}}
    result = _lookup("key.nested", data)
    assert result is None


def test_lookup_non_dict_intermediate():
    set_language("en")
    result = _lookup("detected.type")
    assert result is None


def test_lookup_non_string_result():
    set_language("en")
    result = _lookup("detected.nonexistent")
    assert result is None
