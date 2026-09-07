from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Exams', '0011_remove_studentsheetextractversion_contains_code_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='question_paper_data',
            field=models.BinaryField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='exam',
            name='question_paper_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='exam',
            name='answer_key_data',
            field=models.BinaryField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='exam',
            name='answer_key_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='submission',
            name='file_data',
            field=models.BinaryField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='submission',
            name='file_name',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
