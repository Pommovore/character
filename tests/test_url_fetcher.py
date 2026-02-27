"""Tests pour l'utilitaire de détection et téléchargement d'URL.

Ce module contient des tests unitaires pour les fonctions is_url et fetch_text_content
du module url_fetcher.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.utils.url_fetcher import is_url, fetch_text_content


class TestIsUrl:
    """Tests pour la fonction is_url."""

    def test_valid_http_url(self):
        """Vérifie qu'une URL HTTP valide est détectée."""
        assert is_url("http://example.com/page.txt") is True

    def test_valid_https_url(self):
        """Vérifie qu'une URL HTTPS valide est détectée."""
        assert is_url("https://example.com/document") is True

    def test_url_with_whitespace(self):
        """Vérifie qu'une URL avec des espaces autour est détectée."""
        assert is_url("  https://example.com/page  ") is True

    def test_plain_text(self):
        """Vérifie qu'un texte normal n'est pas détecté comme URL."""
        assert is_url("Harry Potter est un sorcier courageux") is False

    def test_empty_string(self):
        """Vérifie qu'une chaîne vide n'est pas détectée comme URL."""
        assert is_url("") is False

    def test_ftp_url(self):
        """Vérifie qu'une URL FTP n'est pas détectée (seuls http/https sont acceptés)."""
        assert is_url("ftp://example.com/file.txt") is False

    def test_url_without_scheme(self):
        """Vérifie qu'une URL sans schéma n'est pas détectée."""
        assert is_url("example.com/page") is False

    def test_url_without_netloc(self):
        """Vérifie qu'un schéma seul sans domaine n'est pas détecté."""
        assert is_url("http://") is False


class TestFetchTextContent:
    """Tests pour la fonction fetch_text_content."""

    @pytest.mark.asyncio
    async def test_successful_download(self):
        """Vérifie le téléchargement réussi d'un contenu textuel."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/plain; charset=utf-8"}
        mock_response.content = b"Contenu de test"
        mock_response.text = "Contenu de test"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.utils.url_fetcher.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_text_content("https://example.com/page.txt")
            assert result == "Contenu de test"

    @pytest.mark.asyncio
    async def test_non_text_content_type(self):
        """Vérifie le rejet d'un contenu non textuel."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.utils.url_fetcher.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="n'est pas textuel"):
                await fetch_text_content("https://example.com/file.pdf")

    @pytest.mark.asyncio
    async def test_content_too_large(self):
        """Vérifie le rejet d'un contenu dépassant la taille maximale."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/html"}
        mock_response.content = b"x" * 2_000_000  # 2 Mo, au-dessus de la limite
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.utils.url_fetcher.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="trop volumineux"):
                await fetch_text_content("https://example.com/big-page")

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Vérifie la gestion d'un timeout lors du téléchargement."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.utils.url_fetcher.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Délai d'attente"):
                await fetch_text_content("https://example.com/slow")

    @pytest.mark.asyncio
    async def test_http_error(self):
        """Vérifie la gestion d'une erreur HTTP (ex: 404)."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.utils.url_fetcher.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Erreur HTTP 404"):
                await fetch_text_content("https://example.com/not-found")

    @pytest.mark.asyncio
    async def test_json_content_type_accepted(self):
        """Vérifie que le type application/json est accepté comme contenu textuel."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = b'{"key": "value"}'
        mock_response.text = '{"key": "value"}'
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.utils.url_fetcher.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_text_content("https://api.example.com/data")
            assert result == '{"key": "value"}'
