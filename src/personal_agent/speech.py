from xml.sax.saxutils import escape, quoteattr

import httpx

from personal_agent.settings import Settings


class SpeechNotConfiguredError(RuntimeError):
    pass


class SpeechProviderError(RuntimeError):
    pass


class AzureSpeechClient:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http_client = http_client

    async def synthesize_mp3(self, text: str) -> bytes:
        if not self._settings.speech_is_configured:
            raise SpeechNotConfiguredError("Azure Speech is not configured.")
        if not text.strip() or len(text) > 10000:
            raise ValueError("Speech text must contain 1 to 10000 characters.")

        key = self._settings.azure_speech_key.get_secret_value()
        region = "".join(self._settings.azure_speech_region.split()).lower()
        voice = self._settings.azure_speech_voice
        language = "-".join(voice.split("-")[:2])

        ssml = (
            f'<speak version="1.0" '
            f'xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xml:lang={quoteattr(language)}>'
            f'<voice name={quoteattr(voice)}>{escape(text)}</voice>'
            "</speak>"
        )
        endpoint = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        }

        try:
            response = await self._http_client.post(
                endpoint,
                content=ssml.encode("utf-8"),
                headers=headers,
                timeout=35.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SpeechProviderError("Azure Speech request failed.") from exc

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("audio/") or not response.content:
            raise SpeechProviderError("Azure Speech returned no audio.")

        return response.content
