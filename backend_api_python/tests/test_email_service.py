"""SMTP delivery behavior tests; no network access is used."""
from unittest.mock import MagicMock, patch

from app.services.email_service import EmailService


def _configured_service(monkeypatch, **values):
    defaults = {
        "SMTP_HOST": "smtp.example.test",
        "SMTP_PORT": "587",
        "SMTP_USER": "sender@example.test",
        "SMTP_PASSWORD": "secret",
        "SMTP_USE_TLS": "true",
        "SMTP_USE_SSL": "false",
    }
    defaults.update(values)
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)
    return EmailService()


def test_send_email_uses_bounded_timeout_and_closes_connection(monkeypatch):
    service = _configured_service(monkeypatch, SMTP_TIMEOUT_SECONDS="7")
    server = MagicMock()
    smtp = MagicMock()
    smtp.return_value.__enter__.return_value = server

    with patch("app.services.email_service.smtplib.SMTP", smtp):
        result = service.send_email("user@example.test", "Test", "<p>Hello</p>")

    assert result == (True, "sent")
    smtp.assert_called_once_with("smtp.example.test", 587, timeout=7)
    server.starttls.assert_called_once_with()
    server.login.assert_called_once_with("sender@example.test", "secret")
    server.sendmail.assert_called_once()
    smtp.return_value.__exit__.assert_called_once()


def test_send_email_closes_connection_when_authentication_fails(monkeypatch):
    service = _configured_service(monkeypatch)
    server = MagicMock()
    server.login.side_effect = RuntimeError("auth failed")
    smtp = MagicMock()
    smtp.return_value.__enter__.return_value = server

    with patch("app.services.email_service.smtplib.SMTP", smtp):
        result = service.send_email("user@example.test", "Test", "Hello")

    assert result == (False, "Failed to send email")
    smtp.return_value.__exit__.assert_called_once()
    server.sendmail.assert_not_called()


def test_send_email_uses_ssl_without_starttls(monkeypatch):
    service = _configured_service(monkeypatch, SMTP_USE_SSL="true", SMTP_USE_TLS="true")
    server = MagicMock()
    smtp_ssl = MagicMock()
    smtp_ssl.return_value.__enter__.return_value = server

    with patch("app.services.email_service.smtplib.SMTP_SSL", smtp_ssl):
        result = service.send_email("user@example.test", "Test", "Hello")

    assert result == (True, "sent")
    smtp_ssl.assert_called_once_with("smtp.example.test", 587, timeout=15)
    server.starttls.assert_not_called()
