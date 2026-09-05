from __future__ import annotations

_INSTALLED = False
_ORIGINAL_REFRESH = None


def install() -> None:
    global _INSTALLED, _ORIGINAL_REFRESH
    if _INSTALLED:
        return

    from services.learned_recipe_service import LearnedRecipeService
    from services.lorebook_service import LorebookService
    from ui import collectibles_dashboard_page

    existing_routes = {spec.route for spec in collectibles_dashboard_page.DASHBOARD_SPECS}
    additions = []
    if "Furnishing Plans" not in existing_routes:
        additions.append(
            collectibles_dashboard_page.DashboardSpec(
                "Furnishing Plans",
                "Furnishing Plans",
                (),
                "bar",
                "⌂",
            )
        )
    if "Recipes" not in existing_routes:
        additions.append(
            collectibles_dashboard_page.DashboardSpec(
                "Recipes",
                "Recipes",
                (),
                "bar",
                "✦",
            )
        )
    if "Lorebooks" not in existing_routes:
        additions.append(
            collectibles_dashboard_page.DashboardSpec(
                "Lorebooks",
                "Lorebooks",
                (),
                "shield",
                "▤",
            )
        )

    if additions:
        collectibles_dashboard_page.DASHBOARD_SPECS = (
            *collectibles_dashboard_page.DASHBOARD_SPECS,
            *additions,
        )

    _ORIGINAL_REFRESH = collectibles_dashboard_page.CollectiblesDashboardPage.refresh

    def refresh_with_reference_ledgers(self) -> None:
        _ORIGINAL_REFRESH(self)
        if not self.service.available:
            return

        database_path = self.service.database_path
        active_profile = str(getattr(self.service, "active_profile", "Default") or "Default")

        recipe_service = LearnedRecipeService(database_path)
        lorebook_service = LorebookService(database_path)
        try:
            if hasattr(recipe_service, "set_active_profile"):
                recipe_service.set_active_profile(active_profile)
            if hasattr(lorebook_service, "set_active_profile"):
                lorebook_service.set_active_profile(active_profile)

            special: dict[str, tuple[int, int]] = {
                "Furnishing Plans": recipe_service.progress_summary("Furnishing Plans"),
                "Recipes": recipe_service.progress_summary("Recipes"),
                "Lorebooks": lorebook_service.progress_summary(),
            }

            for tile in self._tiles:
                progress = special.get(tile.spec.route)
                if progress is not None:
                    tile.set_progress(*progress)

            base_owned, base_total = self.service.progress_summary()
            special_owned = sum(owned for owned, _total in special.values())
            special_total = sum(total for _owned, total in special.values())
            overall_owned = base_owned + special_owned
            overall_total = base_total + special_total
            overall_percent = collectibles_dashboard_page._percent(overall_owned, overall_total)

            self.overall_progress.setValue(overall_percent)
            self.overall_progress.setFormat(f"{overall_percent}%")
            self.overall_count.setText(
                f"{overall_owned:,} / {overall_total:,} collection entries secured"
            )

            populated = sum(1 for tile in self._tiles if int(getattr(tile, "total", 0)) > 0)
            self.status.info(
                f"{populated} populated dashboard ledgers · "
                f"{overall_owned:,}/{overall_total:,} collection entries secured."
            )
        finally:
            recipe_service.close()
            lorebook_service.close()

    collectibles_dashboard_page.CollectiblesDashboardPage.refresh = refresh_with_reference_ledgers
    _INSTALLED = True
