"""Маршруты настроек приложения (только для администратора)."""

from flask import flash, redirect, render_template, url_for

from app.modules.auth.decorators import admin_required
from app.modules.settings import settings_bp
from app.modules.settings.forms import SettingsForm
from app.modules.settings.services import (
    get_float_setting,
    get_setting,
    set_setting,
)


@settings_bp.route("/", methods=["GET", "POST"])
@admin_required
def settings_edit():
    form = SettingsForm()
    if form.validate_on_submit():
        set_setting("feed_url", form.feed_url.data)
        set_setting("tiny_api_key", form.tiny_api_key.data)
        set_setting("dollar_exchange_rate", form.dollar_exchange_rate.data)
        flash("Настройки сохранены.", "success")
        return redirect(url_for("settings.settings_edit"))
    form.feed_url.data = get_setting("feed_url")
    form.tiny_api_key.data = get_setting("tiny_api_key")
    form.dollar_exchange_rate.data = get_float_setting("dollar_exchange_rate")
    return render_template("settings_form.html", form=form)
