from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Exams', '0013_alter_extractedquestionanswer_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentsheetextractversion',
            name='primary_language',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='studentsheetextractversion',
            name='model_used',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='studentsheetextractversion',
            name='processing_time_ms',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='extractedquestionanswer',
            name='contains_math',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='extractedquestionanswer',
            name='contains_diagram',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='extractedquestionanswer',
            name='contains_code',
            field=models.BooleanField(default=False),
        ),
    ]
