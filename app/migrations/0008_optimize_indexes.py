# Generated database optimization migration
# This migration adds indexes to frequently queried fields for better performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0007_alter_userexamanswer_selected_choice_number'),  # Adjust to your latest migration
    ]

    operations = [
        # Index for UserProfile queries
        migrations.AddIndex(
            model_name='userprofile',
            index=models.Index(fields=['phone_number'], name='phone_idx'),
        ),
        migrations.AddIndex(
            model_name='userprofile',
            index=models.Index(fields=['email'], name='email_idx'),
        ),
        migrations.AddIndex(
            model_name='userprofile',
            index=models.Index(fields=['is_active'], name='active_idx'),
        ),
        
        # Index for Subscription queries
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['user'], name='sub_user_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['expires_at'], name='sub_expires_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['otp_verified'], name='sub_otp_verified_idx'),
        ),
        
        # Index for Exam queries
        migrations.AddIndex(
            model_name='exam',
            index=models.Index(fields=['exam_type', 'for_scheduling'], name='exam_type_scheduling_idx'),
        ),
        migrations.AddIndex(
            model_name='exam',
            index=models.Index(fields=['created_at'], name='exam_created_idx'),
        ),
        migrations.AddIndex(
            model_name='exam',
            index=models.Index(fields=['is_active'], name='exam_active_idx'),
        ),
        
        # Index for ScheduledExam queries
        migrations.AddIndex(
            model_name='scheduledexam',
            index=models.Index(fields=['scheduled_datetime'], name='scheduled_datetime_idx'),
        ),
        migrations.AddIndex(
            model_name='scheduledexam',
            index=models.Index(fields=['exam'], name='scheduled_exam_idx'),
        ),
        
        # Index for UserExam queries
        migrations.AddIndex(
            model_name='userexam',
            index=models.Index(fields=['user', 'exam'], name='user_exam_idx'),
        ),
        migrations.AddIndex(
            model_name='userexam',
            index=models.Index(fields=['completed_at'], name='userexam_completed_idx'),
        ),
        migrations.AddIndex(
            model_name='userexam',
            index=models.Index(fields=['user', 'completed_at'], name='user_completed_idx'),
        ),
        
        # Index for UserExamAnswer queries
        migrations.AddIndex(
            model_name='userexamanswer',
            index=models.Index(fields=['user_exam'], name='answer_exam_idx'),
        ),
        migrations.AddIndex(
            model_name='userexamanswer',
            index=models.Index(fields=['question'], name='answer_question_idx'),
        ),
        
        # Index for Course queries
        migrations.AddIndex(
            model_name='course',
            index=models.Index(fields=['slug'], name='course_slug_idx'),
        ),
        migrations.AddIndex(
            model_name='course',
            index=models.Index(fields=['category'], name='course_category_idx'),
        ),
        
        # Index for Question queries
        migrations.AddIndex(
            model_name='question',
            index=models.Index(fields=['question_type'], name='question_type_idx'),
        ),
        migrations.AddIndex(
            model_name='question',
            index=models.Index(fields=['order'], name='question_order_idx'),
        ),
        
        # Index for RoadSign queries
        migrations.AddIndex(
            model_name='roadsign',
            index=models.Index(fields=['is_active'], name='roadsign_active_idx'),
        ),
        
        # Index for Payment queries
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['user'], name='payment_user_idx'),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['created_at'], name='payment_created_idx'),
        ),
        
        # Index for UserActivity queries
        migrations.AddIndex(
            model_name='useractivity',
            index=models.Index(fields=['user', 'timestamp'], name='activity_user_time_idx'),
        ),
        
        # Index for Notification queries
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', 'is_read'], name='notification_user_read_idx'),
        ),
    ]
