import bot


def test_main_registers_every_command_and_schedules_jobs(monkeypatch):
    registered_commands = set()
    scheduled = {}

    class FakeJobQueue:
        def run_daily(self, callback, time):
            scheduled.setdefault("daily", []).append(callback)

        def run_repeating(self, callback, interval, first=0):
            scheduled["repeating"] = callback

    class FakeApplication:
        job_queue = FakeJobQueue()

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
    monkeypatch.setattr(bot, "CHAT_ID", "12345")

    bot.main()

    assert registered_commands == {
        "start", "dados", "volume", "relatorio",
        "addticker", "removeticker", "listtickers", "alerta",
    }
    assert scheduled["daily"] == [bot.send_daily_summary, bot.send_daily_summary]
    assert scheduled["repeating"] is bot.check_alerts


def test_main_skips_scheduling_without_chat_id(monkeypatch):
    class FakeApplication:
        def add_handler(self, _handler):
            pass

        def run_polling(self):
            pass

    class FakeBuilder:
        def token(self, _token):
            return self

        def build(self):
            return FakeApplication()

    monkeypatch.setattr(bot, "ApplicationBuilder", lambda: FakeBuilder())
    monkeypatch.setattr(bot, "CHAT_ID", "")

    bot.main()  # would raise if it touched .job_queue on a bare FakeApplication
