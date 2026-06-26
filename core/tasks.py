"""
Celery tasks for background processing
"""
from celery import shared_task
from django.utils import timezone

from .models import AsyncJob, CustomUser, Device, Notification, Salary, SalaryTemplate
from .email_service import EmailNotificationService
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


def _get_job(job_id):
    return AsyncJob.objects.get(id=job_id)


@shared_task(bind=True)
def sync_zkteco_device_task(self, job_id):
    job = _get_job(job_id)
    job.mark_running(self.request.id)
    try:
        from datetime import datetime
        from .zkteco_service import zkteco_service

        payload = job.payload
        device_ip = payload['device_ip']
        device_port = int(payload.get('device_port') or 4370)
        start_date = payload.get('start_date')
        end_date = payload.get('end_date')

        start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None

        logger.info("Starting ZKTeco sync for %s:%s job=%s", device_ip, device_port, job_id)
        attendance_logs = zkteco_service.fetch_attendance_from_device(
            device_ip, device_port, start_dt, end_dt
        )
        device_info = {'ip_address': device_ip, 'port': device_port, 'name': f'ZKTeco_{device_ip}'}
        sync_result = zkteco_service.sync_attendance_to_database(attendance_logs, device_info)
        if isinstance(sync_result, tuple):
            synced_count, error_count = sync_result
        elif sync_result is False:
            synced_count, error_count = 0, len(attendance_logs)
        else:
            synced_count, error_count = 0, 0

        result = {
            'synced_count': synced_count,
            'error_count': error_count,
            'total_logs': len(attendance_logs),
        }
        job.mark_completed(result)
        logger.info("Completed ZKTeco sync job=%s result=%s", job_id, result)
        return result
    except Exception as exc:
        logger.exception("ZKTeco device sync failed job=%s", job_id)
        job.mark_failed(exc)
        raise


@shared_task(bind=True)
def sync_all_zkteco_devices_task(self, job_id):
    job = _get_job(job_id)
    job.mark_running(self.request.id)
    try:
        from datetime import datetime
        from .zkteco_service import zkteco_service

        payload = job.payload
        start_date = payload.get('start_date')
        end_date = payload.get('end_date')
        start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None

        devices = list(Device.objects.filter(device_type='zkteco', is_active=True).values(
            'ip_address', 'port', 'name', 'office'
        ))
        all_attendance = zkteco_service.fetch_all_devices_attendance(devices, start_dt, end_dt)

        total_synced = 0
        total_errors = 0
        device_results = {}
        for device_name, device_data in all_attendance.items():
            logs = device_data.get('attendance_logs', [])
            sync_result = zkteco_service.sync_attendance_to_database(logs, device_data['device_info'])
            if isinstance(sync_result, tuple):
                synced_count, error_count = sync_result
            else:
                synced_count, error_count = 0, len(logs)
            total_synced += synced_count
            total_errors += error_count
            device_results[device_name] = {
                'synced_count': synced_count,
                'error_count': error_count,
                'total_logs': len(logs),
            }

        result = {
            'total_synced': total_synced,
            'total_errors': total_errors,
            'device_results': device_results,
        }
        job.mark_completed(result)
        return result
    except Exception as exc:
        logger.exception("All-device ZKTeco sync failed job=%s", job_id)
        job.mark_failed(exc)
        raise


@shared_task(bind=True)
def salary_bulk_create_task(self, job_id):
    job = _get_job(job_id)
    job.mark_running(self.request.id)
    try:
        payload = job.payload
        created_by = job.requested_by
        salary_month = timezone.datetime.fromisoformat(payload['salary_month']).date()
        template_id = payload.get('template_id')
        basic_pay = Decimal(str(payload.get('basic_pay') or '0'))
        increment = Decimal(str(payload.get('increment') or '0'))
        attendance_based = payload.get('attendance_based', True)

        created_ids = []
        errors = []
        template = SalaryTemplate.objects.filter(id=template_id).first() if template_id else None

        for employee_id in payload.get('employee_ids', []):
            try:
                employee = CustomUser.objects.select_related('office', 'designation').get(id=employee_id)
                if Salary.objects.filter(employee=employee, salary_month=salary_month).exists():
                    errors.append(f"Salary already exists for {employee.get_full_name()} for {salary_month}")
                    continue

                if template:
                    if not employee.designation or not employee.office:
                        errors.append(f"Template cannot match employee {employee.get_full_name()} without designation/office")
                        continue
                    if employee.designation_id != template.designation_id or employee.office_id != template.office_id:
                        errors.append(f"Template does not match employee {employee.get_full_name()}")
                        continue
                    salary_data = {
                        'employee': employee,
                        'basic_pay': template.basic_pay,
                        'per_day_pay': getattr(template, 'per_day_pay', 0),
                        'salary_month': salary_month,
                        'attendance_based': attendance_based,
                        'is_auto_calculated': True,
                        'created_by': created_by,
                    }
                else:
                    salary_data = {
                        'employee': employee,
                        'basic_pay': basic_pay,
                        'increment': increment,
                        'salary_month': salary_month,
                        'attendance_based': attendance_based,
                        'is_auto_calculated': True,
                        'created_by': created_by,
                    }
                if employee.pay_bank_name:
                    salary_data['Bank_name'] = employee.pay_bank_name

                salary = Salary.objects.create(**salary_data)
                created_ids.append(str(salary.id))
            except CustomUser.DoesNotExist:
                errors.append(f"Employee with ID {employee_id} not found")
            except Exception as exc:
                logger.exception("Salary bulk create error for employee=%s job=%s", employee_id, job_id)
                errors.append(f"Error creating salary for employee {employee_id}: {exc}")

        result = {'created_salary_ids': created_ids, 'total_created': len(created_ids), 'errors': errors}
        job.mark_completed(result)
        return result
    except Exception as exc:
        logger.exception("Salary bulk create failed job=%s", job_id)
        job.mark_failed(exc)
        raise


@shared_task
def broadcast_attendance_update_task(attendance_data):
    from .consumers import broadcast_attendance_update_sync

    try:
        broadcast_attendance_update_sync(attendance_data)
    except Exception as exc:
        logger.warning("Attendance broadcast failed: %s", exc)


@shared_task
def send_notification_email(notification_id, urgent=False):
    try:
        notification = Notification.objects.select_related('user').get(id=notification_id)
    except Notification.DoesNotExist:
        logger.warning("Notification email skipped; notification %s not found", notification_id)
        return {'sent': 0, 'failed': 1}

    if not notification.user.email or not notification.user.is_active:
        return {'sent': 0, 'failed': 0}

    try:
        if urgent:
            EmailNotificationService.send_urgent_notification_email(notification)
        else:
            EmailNotificationService.send_notification_email(notification)
        notification.is_email_sent = True
        notification.save(update_fields=['is_email_sent'])
        return {'sent': 1, 'failed': 0}
    except Exception as exc:
        logger.exception("Failed to send notification email id=%s", notification_id)
        return {'sent': 0, 'failed': 1, 'error': str(exc)}


@shared_task
def send_bulk_notification_emails(notification_ids):
    """
    Send emails for bulk notifications in the background
    """
    try:
        notifications = Notification.objects.filter(id__in=notification_ids)
        sent_count = 0
        failed_count = 0
        
        for notification in notifications:
            # Only send emails to active users
            if notification.user.email and not notification.is_email_sent and notification.user.is_active:
                try:
                    EmailNotificationService.send_notification_email(notification)
                    notification.is_email_sent = True
                    notification.save(update_fields=['is_email_sent'])
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send email for notification {notification.id}: {e}")
                    failed_count += 1
            elif not notification.user.is_active:
                logger.info(f"Skipping email for inactive user: {notification.user.get_full_name()} ({notification.user.email})")
        
        logger.info(f"Email sending completed: {sent_count} sent, {failed_count} failed")
        return {
            'sent': sent_count,
            'failed': failed_count,
            'total': len(notification_ids)
        }
        
    except Exception as e:
        logger.error(f"Error in send_bulk_notification_emails task: {e}")
        return {'error': str(e)}
