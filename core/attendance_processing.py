import logging
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from .models import (
    Attendance,
    AttendanceAuditLog,
    BiometricAssignmentHistory,
    CustomUser,
    DeviceUser,
    DuplicatePunchAttempt,
    ESSLAttendanceLog,
    UnmatchedBiometricPunch,
)

logger = logging.getLogger(__name__)


def normalize_punch_type(value=None, status=None, punch_time=None):
    """Normalize device punch values to the raw log model's in/out choices."""
    if isinstance(status, int):
        return 'out' if status == 1 else 'in'

    value = (str(value or '')).strip().lower()
    if value in ['out', 'check_out', 'checkout', 'exit', '1']:
        return 'out'
    if value in ['in', 'check_in', 'checkin', 'entry', '0']:
        return 'in'

    if punch_time:
        return 'in' if punch_time.hour < 12 else 'out'
    return 'in'


def normalize_timestamp(value):
    """Return a timezone-aware datetime from common ZKTeco timestamp formats."""
    if isinstance(value, datetime):
        timestamp = value
    else:
        timestamp_text = str(value)
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
            try:
                timestamp = datetime.strptime(timestamp_text, fmt)
                break
            except ValueError:
                continue
        else:
            timestamp = datetime.fromisoformat(timestamp_text.replace('Z', '+00:00'))

    if timezone.is_naive(timestamp):
        timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())
    return timestamp


def _safe_biometric_history_user(biometric_id, punch_time):
    """Use assignment history to resolve reused biometric IDs by punch date."""
    assignment = (
        BiometricAssignmentHistory.objects.filter(
            new_biometric_id=str(biometric_id),
            created_at__lte=punch_time,
        )
        .select_related('employee')
        .order_by('-created_at')
        .first()
    )
    if assignment:
        return assignment.employee
    return None


def resolve_employee_for_punch(device, biometric_id, punch_time, device_user_id='', employee_id=''):
    """Resolve a punch to an employee without treating biometric ID as permanent identity."""
    biometric_id = str(biometric_id)
    device_user_id = str(device_user_id or biometric_id)
    employee_id = str(employee_id or '')

    device_mapping = (
        DeviceUser.objects.filter(
            device=device,
            device_user_id=device_user_id,
            is_mapped=True,
            system_user__isnull=False,
        )
        .select_related('system_user')
        .first()
    )
    if device_mapping:
        return device_mapping.system_user, 'device_user_mapping'

    history_user = _safe_biometric_history_user(biometric_id, punch_time)
    if history_user:
        return history_user, 'biometric_assignment_history'

    biometric_users = list(CustomUser.objects.filter(biometric_id=biometric_id)[:2])
    if len(biometric_users) == 1:
        return biometric_users[0], 'unique_current_biometric_id'
    if len(biometric_users) > 1:
        return None, 'ambiguous_biometric_id'

    if employee_id:
        employee = CustomUser.objects.filter(employee_id=employee_id).first()
        if employee:
            return employee, 'employee_id_fallback'

    fallback_employee = CustomUser.objects.filter(employee_id=device_user_id).first()
    if fallback_employee:
        return fallback_employee, 'device_user_id_employee_fallback'

    return None, 'no_matching_employee'


def create_unmatched_punch(device, biometric_id, punch_time, punch_type, source, device_user_id='', raw_payload=None, reason='no_matching_employee'):
    punch, _ = UnmatchedBiometricPunch.objects.get_or_create(
        device=device,
        biometric_id=str(biometric_id),
        punch_time=punch_time,
        defaults={
            'device_user_id': str(device_user_id or biometric_id),
            'punch_type': punch_type,
            'source': source,
            'raw_payload': raw_payload,
            'reason': reason,
        },
    )
    return punch


@transaction.atomic
def record_raw_punch(device, biometric_id, punch_time, punch_type='in', source='zkteco_fetch', device_user_id='', employee_id='', raw_payload=None):
    """Save the raw device punch first, then process final attendance from raw logs."""
    punch_time = normalize_timestamp(punch_time)
    punch_type = normalize_punch_type(punch_type, raw_payload.get('status') if isinstance(raw_payload, dict) else None, punch_time)
    biometric_id = str(biometric_id)
    device_user_id = str(device_user_id or biometric_id)

    existing_log = ESSLAttendanceLog.objects.filter(
        device=device,
        biometric_id=biometric_id,
        punch_time=punch_time,
    ).first()
    if existing_log:
        DuplicatePunchAttempt.objects.create(
            existing_log=existing_log,
            device=device,
            biometric_id=biometric_id,
            device_user_id=device_user_id,
            punch_time=punch_time,
            punch_type=punch_type,
            source=source,
            raw_payload=raw_payload,
        )
        return existing_log, False, 'duplicate'

    employee, match_reason = resolve_employee_for_punch(device, biometric_id, punch_time, device_user_id, employee_id)
    raw_log = ESSLAttendanceLog.objects.create(
        device=device,
        biometric_id=biometric_id,
        device_user_id=device_user_id,
        user=employee,
        punch_time=punch_time,
        punch_type=punch_type,
        source=source,
        raw_payload=raw_payload,
        is_processed=False,
    )

    if not employee:
        create_unmatched_punch(
            device=device,
            biometric_id=biometric_id,
            device_user_id=device_user_id,
            punch_time=punch_time,
            punch_type=punch_type,
            source=source,
            raw_payload=raw_payload,
            reason=match_reason,
        )
        return raw_log, True, 'unmatched'

    process_raw_log_to_attendance(raw_log, source=source)
    return raw_log, True, 'processed'


def process_raw_log_to_attendance(raw_log, source='zkteco_fetch', changed_by=None):
    """Create/update final Attendance from raw logs: earliest punch in, latest punch out."""
    if not raw_log.user:
        return None

    attendance, _ = Attendance.objects.get_or_create(
        user=raw_log.user,
        date=raw_log.punch_time.date(),
        defaults={
            'status': 'present',
            'device': raw_log.device,
            'source': source,
        },
    )

    if attendance.is_locked and not (changed_by and getattr(changed_by, 'is_superuser', False)):
        AttendanceAuditLog.objects.create(
            attendance=attendance,
            employee=attendance.user,
            date=attendance.date,
            old_check_in=attendance.check_in_time,
            new_check_in=attendance.check_in_time,
            old_check_out=attendance.check_out_time,
            new_check_out=attendance.check_out_time,
            old_status=attendance.status,
            new_status=attendance.status,
            old_day_status=attendance.day_status,
            new_day_status=attendance.day_status,
            change_type='locked_modification_attempt',
            source=source,
            was_locked=True,
            changed_by=changed_by,
            reason='Raw punch received for locked payroll month; final attendance not changed.',
        )
        raw_log.is_processed = True
        raw_log.save(update_fields=['is_processed'])
        return attendance

    if attendance.manual_override and source not in ['manual', 'admin_correction']:
        attendance.needs_review = True
        attendance.review_reason = 'manual_override_preserved'
        attendance.save(update_fields=['needs_review', 'review_reason', 'updated_at'])
        raw_log.is_processed = True
        raw_log.save(update_fields=['is_processed'])
        return attendance

    logs = ESSLAttendanceLog.objects.filter(
        user=raw_log.user,
        punch_time__date=raw_log.punch_time.date(),
    ).order_by('punch_time')

    first_log = logs.first()
    last_log = logs.last()
    old_values = {
        'check_in': attendance.check_in_time,
        'check_out': attendance.check_out_time,
        'status': attendance.status,
        'day_status': attendance.day_status,
    }

    attendance.check_in_time = first_log.punch_time if first_log else attendance.check_in_time
    attendance.check_out_time = last_log.punch_time if first_log and last_log and last_log.punch_time != first_log.punch_time else None
    attendance.device = raw_log.device or attendance.device
    attendance.source = source
    attendance.needs_review = bool(attendance.check_in_time and not attendance.check_out_time)
    attendance.review_reason = 'missing_checkout' if attendance.needs_review else ''
    attendance.save()

    if old_values['check_in'] != attendance.check_in_time or old_values['check_out'] != attendance.check_out_time:
        AttendanceAuditLog.objects.create(
            attendance=attendance,
            employee=attendance.user,
            date=attendance.date,
            old_check_in=old_values['check_in'],
            new_check_in=attendance.check_in_time,
            old_check_out=old_values['check_out'],
            new_check_out=attendance.check_out_time,
            old_status=old_values['status'],
            new_status=attendance.status,
            old_day_status=old_values['day_status'],
            new_day_status=attendance.day_status,
            change_type='system_recalculation',
            source=source,
            was_locked=False,
            changed_by=changed_by,
            reason='Attendance recalculated from raw biometric punches.',
        )

    logs.update(is_processed=True)
    return attendance
