from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from acorn.marketplace import (
    _github_get,
    install_from_github,
    search_all,
    search_github,
)


def test_search_github_empty_query():
    results = search_github("")
    assert isinstance(results, list)


def test_search_all_empty_query():
    results = search_all("")
    assert isinstance(results, list)


def test_install_from_github_invalid_repo():
    result = install_from_github("nonexistent/repo-that-does-not-exist-12345")
    assert result is None


@patch("acorn.marketplace.urllib.request.urlopen")
def test_github_get_success(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"id": 1, "name": "test"}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp
    result = _github_get("/repos/test/test")
    assert result is not None
    assert result["id"] == 1


@patch("acorn.marketplace.urllib.request.urlopen")
def test_github_get_http_error(mock_urlopen):
    import urllib.error
    mock_urlopen.side_effect = urllib.error.HTTPError(
        "https://api.github.com/test", 404, "Not Found", {}, None
    )
    result = _github_get("/test")
    assert result is None


@patch("acorn.marketplace.urllib.request.urlopen")
def test_github_get_url_error(mock_urlopen):
    import urllib.error
    mock_urlopen.side_effect = urllib.error.URLError("timeout")
    result = _github_get("/test")
    assert result is None


@patch("acorn.marketplace.urllib.request.urlopen")
def test_github_get_bad_json(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"not json"
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp
    result = _github_get("/test")
    assert result is None


@patch("acorn.marketplace.urllib.request.urlopen")
def test_search_github_with_results(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "items": [
            {"full_name": "user/tpl", "description": "A template", "stargazers_count": 42},
        ]
    }).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp
    results = search_github("template")
    assert len(results) == 1
    assert results[0]["full_name"] == "user/tpl"


@patch("acorn.marketplace.urllib.request.urlopen")
def test_search_github_non_dict(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps([]).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp
    assert search_github("test") == []


@patch("acorn.marketplace.urllib.request.urlopen")
def test_search_all_non_dict(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps([]).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp
    assert search_all("test") == []


def _mock_urlopen_bytes(*args, **kwargs):
    import io
    return io.BytesIO(b"fake zip content")


def _mock_zip_extract(tmpdl, repo_name="repo"):
    def mock_extractall(path):
        extract_dir = Path(path)
        (extract_dir / repo_name).mkdir(parents=True, exist_ok=True)

    def mock_zipfile(*args, **kwargs):
        zf = MagicMock()
        zf.__enter__.return_value = zf
        zf.extractall = mock_extractall
        return zf
    return mock_zipfile


def test_install_from_github_no_extracted_dirs(tmp_path):
    tmpdl = tmp_path / "tmpdl"
    tmpdl.mkdir(parents=True)
    with patch("acorn.marketplace.tempfile.mkdtemp", return_value=str(tmpdl)):
        with patch("acorn.marketplace.urllib.request.urlopen", side_effect=_mock_urlopen_bytes):
            with patch("zipfile.ZipFile", side_effect=_mock_zip_extract(tmpdl)):
                assert install_from_github("user/tpl-repo") is None


def test_install_from_github_no_template_yaml(tmp_path):
    tmpdl = tmp_path / "tmpdl"
    tmpdl.mkdir(parents=True)
    with patch("acorn.marketplace.tempfile.mkdtemp", return_value=str(tmpdl)):
        with patch("acorn.marketplace.urllib.request.urlopen", side_effect=_mock_urlopen_bytes):
            with patch("zipfile.ZipFile", side_effect=_mock_zip_extract(tmpdl)):
                assert install_from_github("user/tpl-repo") is None


def test_install_from_github_invalid_yaml(tmp_path):
    tmpdl = tmp_path / "tmpdl"
    tmpdl.mkdir(parents=True)
    repo_dir = tmpdl / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    (repo_dir / "template.yaml").write_text("name: 123\ninvalid: yaml: [broken\n")
    with patch("acorn.marketplace.tempfile.mkdtemp", return_value=str(tmpdl)):
        with patch("acorn.marketplace.urllib.request.urlopen", side_effect=_mock_urlopen_bytes):
            with patch("zipfile.ZipFile") as mock_zf:
                mock_zf_instance = MagicMock()
                mock_zf.return_value = mock_zf_instance
                mock_zf_instance.__enter__.return_value.extractall = lambda p: None
                assert install_from_github("user/tpl-repo") is None


def test_install_from_github_already_exists(tmp_path):
    tmpdl = tmp_path / "tmpdl"
    tmpdl.mkdir(parents=True)
    def mock_extract_with_template(path):
        extract_dir = Path(path)
        repo_dir = extract_dir / "repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "template.yaml").write_text("name: tpl-repo\ntype: node\nfiles: []\n")
    (tmp_path / "global" / "tpl-repo").mkdir(parents=True)
    with patch("acorn.marketplace.tempfile.mkdtemp", return_value=str(tmpdl)):
        with patch("acorn.marketplace.urllib.request.urlopen", side_effect=_mock_urlopen_bytes):
            with patch("zipfile.ZipFile") as mock_zf:
                mock_zf_instance = MagicMock()
                mock_zf.return_value = mock_zf_instance
                mock_zf_instance.__enter__.return_value.extractall = mock_extract_with_template
                with patch("acorn.marketplace.TEMPLATES_DIR", tmp_path / "global"):
                    assert install_from_github("user/tpl-repo") is None


@patch("acorn.marketplace.urllib.request.urlopen")
@patch("zipfile.ZipFile")
def test_install_from_github_success(mock_zf, mock_urlopen, tmp_path):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"fake zip content"
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    mock_zip_instance = MagicMock()
    mock_zf.return_value = mock_zip_instance

    tmpdl = tmp_path / "tmpdl"
    tmpdl.mkdir(parents=True, exist_ok=True)

    def mock_extractall(path):
        extract_dir = Path(path)
        (extract_dir / "repo").mkdir(parents=True, exist_ok=True)
        (extract_dir / "repo" / "template.yaml").write_text("name: tpl-repo\ndescription: Test\ntype: node\nfiles: []\n")

    mock_zip_instance.__enter__.return_value.extractall = mock_extractall

    with patch("acorn.marketplace.tempfile.mkdtemp", return_value=str(tmpdl)):
        with patch("acorn.marketplace.TEMPLATES_DIR", tmp_path / "global"):
            result = install_from_github("user/tpl-repo")
            assert result is not None
            assert (tmp_path / "global" / "tpl-repo").exists()


@patch("acorn.marketplace.urllib.request.urlopen")
def test_install_from_github_no_release(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps([]).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp
    result = install_from_github("user/tpl-repo")
    assert result is None


@patch("acorn.marketplace.urllib.request.urlopen")
def test_search_all_with_results(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "items": [
            {"full_name": "user/tpl", "description": "desc", "stargazers_count": 5},
        ]
    }).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp
    results = search_all("test")
    assert len(results) >= 1


def test_install_from_github_dry_run():
    result = install_from_github("user/tpl-repo", dry_run=True)
    assert result is None


@patch("acorn.marketplace.tempfile.mkdtemp")
@patch("acorn.marketplace.urllib.request.urlopen")
def test_install_from_github_no_content(mock_urlopen, mock_mkdtemp, tmp_path):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b"zip"
    mock_mkdtemp.return_value = str(tmp_path)
    with patch("zipfile.ZipFile") as mock_zip:
        mock_zip.return_value.__enter__.return_value.extractall = MagicMock()
        result = install_from_github("user/tpl-repo")
    assert result is None
