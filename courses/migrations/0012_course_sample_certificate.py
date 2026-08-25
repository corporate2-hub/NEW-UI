from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0011_alter_certificatetemplate_course_title_x_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='sample_certificate',
            field=models.ImageField(blank=True, null=True, upload_to='course_certificates/'),
        ),
    ]

