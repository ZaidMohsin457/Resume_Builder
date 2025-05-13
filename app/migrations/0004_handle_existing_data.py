from django.db import migrations, models
import django.db.models.deletion

def handle_existing_data(apps, schema_editor):
    ResumeAnalysis = apps.get_model('app', 'ResumeAnalysis')
    # Delete any ResumeAnalysis records that don't have a resume
    ResumeAnalysis.objects.filter(resume__isnull=True).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_job_alter_resume_job_titles_alter_resume_skills_and_more'),
    ]

    operations = [
        migrations.RunPython(handle_existing_data),
        migrations.AlterField(
            model_name='resumeanalysis',
            name='resume',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='app.resume'),
        ),
        migrations.AlterField(
            model_name='resumeanalysis',
            name='recommendations',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='resumeanalysis',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]