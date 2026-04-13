from amr_ui.views import camera, home, logs, navigation, radar, settings, status


def route(page: str, t: dict) -> None:
    """Dispatch to the view for the currently selected sidebar page."""
    pages = t["sidebar_pages"]
    handlers = {
        pages[0]: home.render,
        pages[1]: radar.render,
        pages[2]: navigation.render,
        pages[3]: camera.render,
        pages[4]: status.render,
        pages[5]: logs.render,
        pages[6]: settings.render,
    }
    handler = handlers.get(page)
    if handler is not None:
        handler(t)
