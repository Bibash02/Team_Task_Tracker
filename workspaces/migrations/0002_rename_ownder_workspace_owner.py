from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="workspace",
            old_name="ownder",
            new_name="owner",
        ),
    ]
