# Generated by Django 5.2 on 2025-04-04 13:25

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Shops',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shopName', models.CharField(max_length=30, unique=True)),
                ('freeRefillInterval', models.IntegerField(help_text='Number of paid refills needed to qualify for one free refill.')),
                ('phone_number', models.CharField(default='0700000000', max_length=13)),
            ],
            options={
                'verbose_name_plural': 'Shops',
            },
        ),
    ]
