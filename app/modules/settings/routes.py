"""Маршруты настроек приложения (только для администратора)."""

from flask import flash, redirect, render_template, url_for

from app.extensions import db
from app.modules.auth.decorators import admin_required
from app.modules.settings import settings_bp
from app.modules.settings.forms import SettingsForm
from app.modules.settings.services import get_setting, set_setting


@settings_bp.route("/", methods=["GET", "POST"])
@admin_required
def settings_edit():
    form = SettingsForm()
    if form.validate_on_submit():
        set_setting("feed_url", form.feed_url.data)
        set_setting("tiny_api_key", form.tiny_api_key.data)
        flash("Настройки сохранены.", "success")
        return redirect(url_for("settings.settings_edit"))
    form.feed_url.data = get_setting("feed_url")
    form.tiny_api_key.data = get_setting("tiny_api_key")
    return render_template("settings_form.html", form=form)