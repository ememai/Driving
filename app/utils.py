from .models import *
from datetime import datetime, timedelta, time, date
from django.utils.timezone import now, localtime
import random
from django.utils import timezone
from django.conf import settings
from django.db import DatabaseError, transaction
from django.core.mail import send_mail
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import re
from django.db import connections

# Configure logger for this module
logger = logging.getLogger(__name__)


QUESTIONS_PER_EXAM = 20
ROTATION_SCOPE = "all-exams"


class ExamQuestionSelectionError(ValueError):
    """Raised when an exam cannot be made without breaking its safeguards."""


def _existing_exam_question_sets(history_limit):
    """Return question IDs for the most recent saved exam forms.

    Rotation usage is intentionally kept forever within its active round, but
    similarity is a recency safeguard.  Comparing against every historical
    exam would eventually make a finite question bank impossible to use.
    """
    recent_exam_ids = list(
        Exam.objects.order_by("-created_at", "-pk").values_list("id", flat=True)[:history_limit]
    )
    question_sets = {}
    through_model = Exam.questions.through
    for exam_id, question_id in through_model.objects.filter(
        exam_id__in=recent_exam_ids
    ).values_list("exam_id", "question_id"):
        question_sets.setdefault(exam_id, set()).add(question_id)
    return [question_sets[exam_id] for exam_id in recent_exam_ids if exam_id in question_sets]


def _build_overlap_limited_candidate(required_ids, candidate_ids, size, previous_forms, max_shared):
    """Build a form while backtracking around choices that block completion."""
    selected = set(required_ids)
    overlap_counts = [sum(question_id in form for question_id in selected) for form in previous_forms]
    if any(count > max_shared for count in overlap_counts):
        return None

    question_forms = {}
    for form_index, form in enumerate(previous_forms):
        for question_id in form:
            question_forms.setdefault(question_id, []).append(form_index)

    available_ids = list(set(candidate_ids) - selected)
    random.shuffle(available_ids)
    search_budget = 10000
    visited_states = 0

    def search(selected_ids, current_overlap_counts, remaining_ids):
        nonlocal visited_states
        visited_states += 1
        if visited_states > search_budget:
            return None

        slots_needed = size - len(selected_ids)
        if slots_needed == 0:
            return selected_ids

        allowed_ids = [
            question_id
            for question_id in remaining_ids
            if all(
                current_overlap_counts[form_index] < max_shared
                for form_index in question_forms.get(question_id, [])
            )
        ]
        if len(allowed_ids) < slots_needed:
            return None

        unconstrained_count = sum(not question_forms.get(question_id) for question_id in allowed_ids)
        remaining_capacity = sum(
            max_shared - current_overlap_counts[form_index]
            for form_index, form in enumerate(previous_forms)
            if any(question_id in form for question_id in allowed_ids)
        )
        if unconstrained_count + remaining_capacity < slots_needed:
            return None

        # Try the least constrained questions first, but retain alternatives
        # when a choice would leave too few compatible questions to finish.
        allowed_ids.sort(key=lambda question_id: len(question_forms.get(question_id, [])))
        for index, question_id in enumerate(allowed_ids):
            next_overlap_counts = current_overlap_counts.copy()
            for form_index in question_forms.get(question_id, []):
                next_overlap_counts[form_index] += 1
            result = search(
                selected_ids | {question_id},
                next_overlap_counts,
                allowed_ids[index + 1 :],
            )
            if result is not None:
                return result
            if visited_states > search_budget:
                return None

        return None

    return search(selected, overlap_counts, available_ids)


def reserve_rotated_questions(
    questions_per_exam=QUESTIONS_PER_EXAM,
    history_reduced_callback=None,
):
    """Reserve questions without repeats in a round or similar exam forms.

    Call this inside the transaction that creates the ``Exam``.  The database
    state makes the rotation survive restarts and serializes concurrent workers.
    """
    if questions_per_exam < 1:
        raise ValueError("questions_per_exam must be at least 1.")

    max_shared, history_limit = get_exam_generation_settings()
    if max_shared < 0 or max_shared >= questions_per_exam:
        raise ValueError(
            "EXAM_MAX_SHARED_QUESTIONS must be between 0 and questions_per_exam - 1."
        )
    if history_limit < 1:
        raise ValueError("EXAM_SIMILARITY_HISTORY_LIMIT must be at least 1.")

    with transaction.atomic():
        rotation, _ = ExamQuestionRotation.objects.get_or_create(scope=ROTATION_SCOPE)
        rotation = ExamQuestionRotation.objects.select_for_update().get(pk=rotation.pk)

        all_question_ids = list(Question.objects.order_by("id").values_list("id", flat=True))
        if len(all_question_ids) < questions_per_exam:
            raise ExamQuestionSelectionError(
                f"At least {questions_per_exam} questions are required; only {len(all_question_ids)} exist."
            )

        used_ids = set(
            ExamQuestionRotationUsage.objects.filter(
                rotation=rotation,
                round_number=rotation.current_round,
            ).values_list("question_id", flat=True)
        )
        unused_ids = [question_id for question_id in all_question_ids if question_id not in used_ids]
        previous_forms = _existing_exam_question_sets(history_limit)

        # A boundary form finishes the current round before drawing its extra
        # slots from the next one.  Therefore no question repeats before every
        # question in the bank has appeared.
        needed_from_next_round = max(0, questions_per_exam - len(unused_ids))
        next_round_choices = (
            [question_id for question_id in all_question_ids if question_id not in unused_ids]
            if needed_from_next_round
            else []
        )

        # At a round boundary every remaining question is mandatory; only the
        # extra slots may come from the next one. Otherwise, draw from unused
        # questions in this round.
        required_ids = unused_ids if needed_from_next_round else []
        selectable_ids = next_round_choices if needed_from_next_round else unused_ids
        available_history = len(previous_forms)

        def find_candidate(history_count):
            return _build_overlap_limited_candidate(
                required_ids,
                selectable_ids,
                questions_per_exam,
                previous_forms[:history_count],
                max_shared,
            )

        selected_history = available_history
        candidate = find_candidate(selected_history)

        if candidate is None:
            upper_bound = available_history
            lower_bound = None
            probe = upper_bound // 2
            while probe >= 1:
                candidate = find_candidate(probe)
                if candidate is not None:
                    lower_bound = probe
                    best_candidate = candidate
                    break
                upper_bound = probe
                probe //= 2

            if lower_bound is not None:
                while upper_bound - lower_bound > 1:
                    probe = (lower_bound + upper_bound) // 2
                    candidate = find_candidate(probe)
                    if candidate is not None:
                        lower_bound = probe
                        best_candidate = candidate
                    else:
                        upper_bound = probe
                selected_history = lower_bound
                candidate = best_candidate
            else:
                selected_history = 0
                candidate = find_candidate(selected_history)

        candidate_ids = list(candidate) if candidate is not None else None

        if candidate_ids is None:
            raise ExamQuestionSelectionError(
                "Could not find a valid exam while respecting the no-repeat rotation and "
                f"the limit of {max_shared} shared question(s) per recent exam."
            )

        if selected_history < available_history:
            logger.warning(
                "Reduced the exam similarity check from %s to %s recent exams to generate a valid form.",
                available_history,
                selected_history,
            )
            if history_reduced_callback:
                history_reduced_callback(available_history, selected_history)

        current_ids = set(candidate_ids) & set(unused_ids)
        ExamQuestionRotationUsage.objects.bulk_create(
            [
                ExamQuestionRotationUsage(
                    rotation=rotation,
                    question_id=question_id,
                    round_number=rotation.current_round,
                )
                for question_id in current_ids
            ]
        )
        if needed_from_next_round:
            next_round = rotation.current_round + 1
            next_ids = set(candidate_ids) - current_ids
            ExamQuestionRotationUsage.objects.bulk_create(
                [
                    ExamQuestionRotationUsage(
                        rotation=rotation,
                        question_id=question_id,
                        round_number=next_round,
                    )
                    for question_id in next_ids
                ]
            )
            rotation.current_round = next_round
            rotation.save(update_fields=["current_round", "updated_at"])

        return candidate_ids


session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
session.mount('https://', HTTPAdapter(max_retries=retries))


def validate_whats_api_credentials():
    """Validate whats_api credentials before use"""
    try:
        response = session.get(
            f"{settings.WHATSAPP_API_URL}/waInstance{settings.INSTANCE_ID}/getStateInstance/{settings.WHATSAPP_API_TOKEN}",
            timeout=15
        )
        if response.status_code == 200:
            return True

        logger.error(f"{response.status_code} whats_api credentials validation failed: {response.text}")
        api_token = getattr(settings, 'WHATSAPP_API_TOKEN', None)
        masked_token = f"{api_token[:4]}...{api_token[-4:]}" if api_token else 'None'
        instance_id = getattr(settings, 'INSTANCE_ID', 'N/A')
        whatsapp_url = getattr(settings, 'WHATSAPP_API_URL', 'N/A')

        # Print/mask credentials info for debugging (do NOT expose tokens in production logs)
        print(f"WhatsApp API URL: {whatsapp_url}")
        print(f"Instance ID: {instance_id}")
        print(f"API Token (masked): {masked_token}")

        # Log full response at debug level only
        logger.debug("WhatsApp validation response body: %s", response.text)
        return False
    except Exception as e:
        logger.error(f"whats_api connection test failed: {str(e)}")
        return False


def get_unverified_subscription(user):
    if not user.is_authenticated:
        return None
    return Subscription.objects.filter(
        user=user,
        otp_code__isnull=False,
        otp_verified=False
    ).first()


def clean_phone_number(number):
    """Clean and validate Rwandan phone number to E.164 format"""
    number = re.sub(r'\D', '', number)  # Remove non-digit characters

    if number.startswith('0') and len(number) == 10:
        # Local format like 0781234567
        return '+250' + number[1:]
    elif number.startswith('250') and len(number) == 12:
        # National format like 250781234567
        return '+' + number
    elif number.startswith('250') and len(number) < 12:
        # Possibly missing digits
        raise ValueError("Incomplete phone number.")
    elif number.startswith('+250') and len(number) == 13:
        # Already in E.164 format
        return number
    else:
        raise ValueError("Invalid phone number format.")


def get_payment_site_settings():
    """Return the shared settings record, creating it with the configured admin number."""
    return SiteSettings.objects.get_or_create(
        pk=1,
        defaults={"phone_number": settings.ADMIN_PHONE_NUMBER},
    )[0]


def get_exam_generation_settings():
    """Read exam-generation safeguards from the database-backed site settings."""
    site_settings = get_payment_site_settings()
    return (
        site_settings.exam_max_shared_questions,
        site_settings.exam_similarity_history_limit,
    )


def notify_admin(message):
    """Send admin notifications via whats_api with improved error handling"""
    try:
        admin_setting = SiteSettings.objects.filter(pk=1).only('phone_number').first()
        configured_number = admin_setting.phone_number if admin_setting else settings.ADMIN_PHONE_NUMBER
    except DatabaseError:
        logger.exception("Could not load admin notification number from the database; using environment setting")
        configured_number = settings.ADMIN_PHONE_NUMBER

    admin_number = re.sub(r'\D', '', configured_number)
    if not admin_number:
        logger.error("Cannot send admin notification - no admin phone number is configured")
        return

    if not validate_whats_api_credentials():
        logger.error("Cannot send admin notification - whats_api credentials invalid")
        return

    try:
        response = session.post(
            f"{settings.WHATSAPP_API_URL}/waInstance{settings.INSTANCE_ID}/sendMessage/{settings.WHATSAPP_API_TOKEN}",
            json={
                "chatId": f"{admin_number}@c.us",
                "message": message
            },
            timeout=30  # Increased timeout
        )

        if response.status_code == 200:
            logger.info("✅ Admin notification sent")
        else:
            logger.error(f"❌ whats_api admin error (HTTP {response.status_code}): {response.text}")
    except Exception as e:
        logger.error(f"🚨 Admin notification failed: {str(e)}", exc_info=True)


def get_support_phone_number():
    """Return the public support phone number configured in admin."""
    try:
        setting = SiteSettings.objects.filter(pk=1).only('support_phone_number').first()
    except DatabaseError:
        logger.exception("Could not load support phone number from the database")
        return "0785287885"
    if setting:
        return setting.support_phone_number
    logger.warning("No admin contact settings found; using the default support phone number")
    return "0785287885"


def phone_or_email():
  username = ''
  user = request.user.objects.get(email=username) if '@' in username else request.user.objects.get(phone_number=username)

  if username == email:
    user.send_otp_email()  # Send OTP
    messages.success(request, 'OTP sent to your email. Verify your account.')
    return redirect('verify_otp', user_id=user.id)
  else:
    return redirect("home")

def set_price_and_duration(plan):
    price = 0
    duration = 0
    if plan == 'Daily':
        price = 1000
        duration = 1
    elif plan == 'Weekly':
        price = 2000
        duration = 7
    elif plan == 'Monthly':
        price = 5000
        duration = 30
    else:
        price = 10000
        duration = None
    return price, duration

def check_exam_availability(hour):
    """
    Determine whether an exam is available at a given hour.

    This function checks for any ScheduledExam objects scheduled on the current day
    whose scheduled_datetime falls within the provided hour (24-hour format). If at
    least one such exam exists, the function returns True.

    Args:
        hour (int): The hour (in 24-hour format) to check for an available exam.

    Returns:
        bool: True if at least one exam is scheduled for that hour today, otherwise False.
    """
    # Get the current date.
    today = timezone.now().date()

    # Query for scheduled exams on today's date where the scheduled hour matches.
    exam_exists = ScheduledExam.objects.filter(
        scheduled_datetime__date=today,
        scheduled_datetime__hour=hour
    ).exists()

    return exam_exists

# def auto_create_exams(number):
#     exams_created = 0
#     for i in range(0, number):
#         try:
#             exam_type, _ = ExamType.objects.get_or_create(name='Ibivanze')
#             questions = Question.objects.order_by('?')[:20]

#             if questions.count() < 20:
#                 print("‼️Not enough questions to create the exam.")
#                 # return redirect('create_exam')

#             # Determine next available hour for exam scheduling
#             last_exam = Exam.objects.filter(for_scheduling=True).order_by('-created_at').first()

#             if last_exam and last_exam.schedule_hour:
#                 try:
#                     last_hour = last_exam.schedule_hour.hour
#                     next_hour = last_hour + 1
#                     if next_hour > 17:
#                         next_hour = 7
#                 except (ValueError, AttributeError):
#                     next_hour = 7

#             else:
#                 next_hour = 7

#             from datetime import time
#             exam_schedule_hour = time(next_hour, 0)


#             exam = Exam.objects.create(
#                 exam_type=exam_type,
#                 schedule_hour=exam_schedule_hour,
#                 duration=20,
#                 for_scheduling=True,
#                 is_active=False,
#             )
#             exam.questions.set(questions)
#             exam.save()
#             questions_list = list(questions.values_list('id', flat=True))
#             exams_created += 1

#             print(f"🏁 Exam '{exam.schedule_hour}' created successfully!")

#         except Exception as e:
#             print(f"Error: {str(e)}")
#     print(f"✅{exams_created} Exams Created successfully!")
#     return exams_created

def auto_create_exams(number, for_scheduling=True, duration=20):
    exams_created = 0
    created_exam_ids = []
    skipped_reasons = []
    reduced_history_windows = []

    # If today is Sunday, skip creating exams
    if timezone.localtime(timezone.now()).weekday() == 6:  # Sunday is represented by 6
        msg = "❌ No exams created on Sundays."
        logger.info(msg)
        total_q = Question.objects.count()
        notify_admin(f"{localtime().strftime('%d-%m-%Y %H:%M')} {msg} Total questions available: {total_q}")
        return exams_created, created_exam_ids

    for i in range(number):
        exam_history_window = []
        try:
            with transaction.atomic():
                exam_type, _ = ExamType.objects.get_or_create(name='Ibivanze')
                question_ids = reserve_rotated_questions(
                    history_reduced_callback=lambda original, used: exam_history_window.append(used)
                )

                last_exam = Exam.objects.filter(for_scheduling=True).order_by('-created_at').first()
                next_hour = (last_exam.schedule_hour.hour + 1 if last_exam and last_exam.schedule_hour else 8) % 24
                next_hour = next_hour if next_hour >= 8 and next_hour <= 15 else 8

                exam_schedule_hour = time(next_hour, 0)
                exam = Exam.objects.create(
                    exam_type=exam_type,
                    schedule_hour=exam_schedule_hour,
                    duration=duration,
                    for_scheduling=for_scheduling,
                    is_active=False,
                )
                exam.questions.set(question_ids)
                created_exam_ids.append(exam.id)
                exams_created += 1
            reduced_history_windows.extend(exam_history_window)

        except ExamQuestionSelectionError as e:
            logger.warning("Skipping exam #%s: %s", i + 1, e)
            skipped_reasons.append(f"Exam #{i+1}: {e}")
            break

        except Exception as e:
            logger.exception("Error creating exam #%s: %s", i + 1, e)
            skipped_reasons.append(f"Exception for exam #{i+1}: {e}")
            continue

    # Send diagnostic admin notification when nothing was created
    total_questions = Question.objects.count()
    if exams_created == 0:
        reason_summary = "; ".join(skipped_reasons) if skipped_reasons else "Unknown"
        notify_admin(
            f"{localtime().strftime('%d-%m-%Y %H:%M')} ❌ Done creating 0 exams. Reasons: {reason_summary}. Total questions available: {total_questions}"
        )
    else:
        history_notice = ""
        if reduced_history_windows:
            history_notice = (
                " Similarity history was reduced to "
                f"{min(reduced_history_windows)}-{max(reduced_history_windows)} recent exams "
                f"for {len(reduced_history_windows)} exam(s); the shared-question limit was unchanged."
            )
        notify_admin(
            f"{localtime().strftime('%d-%m-%Y %H:%M')} ✅ Created {exams_created} exams. "
            f"Skipped: {len(skipped_reasons)}.{history_notice}"
        )

    return exams_created, created_exam_ids

def auto_schedule_recent_exams():
    scheduled_exams_count = 0
    skipped_exams = []
    recent_exams = Exam.objects.filter(
        for_scheduling=True,
        scheduledexam__isnull=True
    ).order_by('-created_at')[:8]
    today = timezone.localtime(timezone.now()).date()
    message = ''

    if today.weekday() == 6:  # Sunday is represented by 6
        message = "❌ No exams to schedule on Sundays."
        print(message)
        return scheduled_exams_count, message

    if not recent_exams.exists():
        message = "ℹ️ No new unscheduled exams found to schedule."
        return scheduled_exams_count, message

    for exam in recent_exams:
        scheduled_time = timezone.make_aware(
            datetime.combine(today, time(hour=exam.schedule_hour.hour, minute=20))
        )
        # Double-check inside a transaction to avoid race conditions where
        # another process may create a ScheduledExam for this exam concurrently.
        try:
            from django.db import transaction, IntegrityError

            with transaction.atomic():
                # Skip if exam already scheduled
                if ScheduledExam.objects.filter(exam=exam).exists():
                    logger.info("Skipping exam %s: already has ScheduledExam", exam.id)
                    skipped_exams.append(
                        f"⏸️ {exam.exam_type.name}: Already scheduled"
                    )
                    continue

                # Skip if that exact datetime is already taken by another scheduled exam
                if ScheduledExam.objects.filter(
                    scheduled_datetime=scheduled_time
                ).exists():
                    logger.info(
                        "Skipping exam %s: datetime %s already taken",
                        exam.id,
                        scheduled_time,
                    )
                    conflicting = ScheduledExam.objects.get(
                        scheduled_datetime=scheduled_time
                    )
                    skipped_exams.append(
                        f"❌ {exam.exam_type.name}: Another exam ({conflicting.exam.exam_type.name if conflicting.exam.exam_type else 'Unknown'}) is already scheduled at {scheduled_time.strftime('%H:%M')}"
                    )
                    continue

                ScheduledExam.objects.create(
                    exam=exam,
                    scheduled_datetime=scheduled_time
                )
                scheduled_exams_count += 1
                message += f"✅ {exam.exam_type.name} scheduled at {scheduled_time.strftime('%Y-%m-%d %H:%M')}\n"
        except IntegrityError:
            # If a concurrent create slipped through, skip and continue.
            skipped_exams.append(
                f"❌ {exam.exam_type.name}: Concurrent scheduling error (try again)"
            )
            continue

    # Build final message with summary
    summary = f"\n\n📊 **Scheduling Summary:**\n"
    summary += f"✅ Successfully scheduled: {scheduled_exams_count}\n"
    summary += f"⏭️ Skipped: {len(skipped_exams)}\n"
    
    if skipped_exams:
        summary += f"\n**Skipped Exams (Reasons):**\n"
        for skip in skipped_exams:
            summary += f"{skip}\n"
    
    return scheduled_exams_count, message + summary


import re

def validate_phone_number(phone_number):
    """
    Validate a phone number to ensure it is in the correct format.

    Args:
        phone_number (str): The phone number to validate.

    Returns:
        bool: True if the phone number is valid, False otherwise.
    """
    # Remove any non-digit characters
    cleaned_number = re.sub(r'\D', '', phone_number)

    # if cleaned_number.startswith('+250') or cleaned_number.startswith('07'):
    return len(cleaned_number) == 10 and cleaned_number.startswith('07') or len(cleaned_number) == 12 and not cleaned_number.startswith('+250')

    # else:
    #     # For other countries, allow only valid E.164 format: starts with '+' and 10-15 digits
    #     return bool(re.fullmatch(r'\+[1-9]\d{9,14}', phone_number))
