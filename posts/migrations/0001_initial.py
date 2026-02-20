"""Initial migration: creates Post and Comment tables."""

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies: list = []

    operations = [
        migrations.CreateModel(
            name="Post",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "instagram_id",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                ("caption", models.TextField(blank=True, null=True)),
                (
                    "media_type",
                    models.CharField(
                        choices=[
                            ("IMAGE", "Image"),
                            ("VIDEO", "Video"),
                            ("CAROUSEL_ALBUM", "Carousel Album"),
                        ],
                        default="IMAGE",
                        max_length=20,
                    ),
                ),
                ("media_url", models.URLField(blank=True, max_length=2048, null=True)),
                ("permalink", models.URLField(max_length=2048)),
                ("timestamp", models.DateTimeField()),
                ("synced_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                "verbose_name": "Post",
                "verbose_name_plural": "Posts",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.CreateModel(
            name="Comment",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="posts.post",
                    ),
                ),
                ("instagram_comment_id", models.CharField(max_length=64)),
                (
                    "text",
                    models.TextField(
                        validators=[
                            django.core.validators.MinLengthValidator(1),
                            django.core.validators.MaxLengthValidator(2200),
                        ]
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Comment",
                "verbose_name_plural": "Comments",
                "ordering": ["-created_at"],
            },
        ),
    ]