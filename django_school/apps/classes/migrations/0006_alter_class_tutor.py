# Generated by Django 3.2.7 on 2021-09-19 14:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_alter_user_slug'),
        ('classes', '0005_alter_class_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='class',
            name='tutor',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='teacher_class', to='users.user'),
        ),
    ]
