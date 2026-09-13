import bot


def test_main_registers_every_command(monkeypatch):
    registered_commands = set()

    class FakeApplication:
        def add_handler(self, handler):
            registered_commands.update(handler.commands)

        def run_polling(self):
            pass

    class FakeBuilder:
        def token(self, _token):
            return self

        def build(self):
            return FakeApplication()

    monkeypatch.setattr(bot, "ApplicationBuilder", lambda: FakeBuilder())

    bot.main()

    assert registered_commands == {
        "start", "dados", "volume", "relatorio",
        "addticker", "removeticker", "listtickers", "alerta",
    }


def test_headers_include_api_key_when_configured(monkeypatch):
    monkeypatch.setattr(bot, "API_KEY", "secret123")
    assert bot._headers() == {"X-API-Key": "secret123"}


def test_headers_empty_when_no_api_key(monkeypatch):
    monkeypatch.setattr(bot, "API_KEY", "")
    assert bot._headers() == {}
