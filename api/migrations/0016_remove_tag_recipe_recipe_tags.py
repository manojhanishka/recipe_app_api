# Generated by Django 5.2.1 on 2025-05-20 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0015_alter_cuisine_name_alter_dietaryrestriction_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tag',
            name='recipe',
        ),
        migrations.AddField(
            model_name='recipe',
            name='tags',
            field=models.ManyToManyField(related_name='recipes', to='api.tag'),
        ),
    ]
