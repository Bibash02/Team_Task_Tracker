from django.contrib import admin
from labels.models import Label

@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "color")
    list_filter = ("workspace",)
