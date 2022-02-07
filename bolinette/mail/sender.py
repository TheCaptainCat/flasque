from bolinette.core import BolinetteContext, WithContext
from bolinette.mail.providers import Mailgun

_providers = {"mailgun": Mailgun}


class Sender(WithContext):
    def __init__(self, context: BolinetteContext):
        super().__init__(context)
        self.provider = None

    def init_app(self):
        provider = self.context.env["mail_provider"]
        if provider:
            provider = provider.lower()
            if provider not in _providers:
                self.context.logger.warning(
                    f'Unknown "{provider}" mail provider. '
                    f'Available: {", ".join(_providers.keys())}'
                )
            else:
                self.provider = _providers[provider](self.context)

    async def send(self, to, subject, content):
        if self.provider:
            try:
                self.provider.send(to, subject, content)
            except Exception as ex:
                self.context.logger.error(str(ex))
