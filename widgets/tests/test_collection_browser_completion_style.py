from widgets.collection_browser import CollectionBrowser, clean_achievement_display_text


class _Provider:
    def __init__(self):
        self._rows = {
            ("Crafting", "Alchemy"): ({"id": 1}, {"id": 2}),
            ("Crafting", "Blacksmithing"): ({"id": 3},),
            ("Empty", "Nothing"): (),
        }

    def subcategories(self, category):
        return tuple(
            subcategory
            for parent, subcategory in self._rows
            if parent == category
        )

    def achievements_in(self, category, subcategory):
        return self._rows.get((category, subcategory), ())


class _Progress:
    def __init__(self, completed=()):
        self.completed = set(completed)

    def is_complete(self, achievement_id):
        return achievement_id in self.completed


class _BrowserLogic:
    def __init__(self, completed=()):
        self.provider = _Provider()
        self.progress_service = _Progress(completed)


def test_player_placeholder_is_removed_from_achievement_display_text():
    assert clean_achievement_display_text("Defeat <<player>> in a duel") == "Defeat in a duel"
    assert clean_achievement_display_text("Earn <<PLAYER>>'s respect!") == "Earn respect!"


def test_subcategory_is_complete_only_when_every_achievement_is_complete():
    partial = _BrowserLogic(completed=(1,))
    complete = _BrowserLogic(completed=(1, 2))

    assert CollectionBrowser._subcategory_complete(partial, "Crafting", "Alchemy") is False
    assert CollectionBrowser._subcategory_complete(complete, "Crafting", "Alchemy") is True


def test_parent_category_requires_all_real_subcategories_to_be_complete():
    almost = _BrowserLogic(completed=(1, 2))
    complete = _BrowserLogic(completed=(1, 2, 3))

    assert CollectionBrowser._category_complete(almost, "Crafting") is False
    assert CollectionBrowser._category_complete(complete, "Crafting") is True


def test_empty_category_does_not_count_as_complete():
    browser = _BrowserLogic(completed=())

    assert CollectionBrowser._category_complete(browser, "Empty") is False
    assert CollectionBrowser._subcategory_complete(browser, "Empty", "Nothing") is False
