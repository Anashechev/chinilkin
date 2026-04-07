import logging
from django.utils import timezone
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from .models import LoginAttempt, IPBlock

logger = logging.getLogger(__name__)

class LoginAttemptMiddleware:
    """
    Middleware для отслеживания попыток входа и блокировки подозрительной активности
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response


@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):
    """Логирование успешного входа через сигнал"""
    try:
        ip_address = _get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Определяем информацию об устройстве
        device_info = _parse_user_agent(user_agent)
        
        # Проверяем на подозрительную активность
        is_suspicious, risk_level, suspicious_reason = _check_suspicious_activity(
            user.username, ip_address, True, request, user
        )
        
        logger.info(f"Successful login: {user.username} from {ip_address}")
        
        # Удаляем старые неудачные попытки для этого пользователя
        LoginAttempt.objects.filter(
            username=user.username,
            ip_address=ip_address,
            is_successful=False
        ).delete()
        
        # Удаляем блокировку для этого IP/устройства при успешном входе
        device_fingerprint = IPBlock._generate_device_fingerprint(user_agent)
        IPBlock.objects.filter(
            ip_address=ip_address,
            device_fingerprint=device_fingerprint
        ).update(is_active=False)
        
        # Создаем запись об успешном входе
        LoginAttempt.objects.create(
            username=user.username,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_info['device_type'],
            browser=device_info['browser'],
            os=device_info['os'],
            event_type='login',
            is_successful=True,
            is_suspicious=is_suspicious,
            risk_level=risk_level,
            reason=suspicious_reason if is_suspicious else '',
            details=f"Успешный вход с устройства: {device_info['browser']} на {device_info['os']}"
        )
    except Exception as e:
        logger.error(f"Error logging successful login: {e}")


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    """Логирование выхода через сигнал"""
    try:
        ip_address = _get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        device_info = _parse_user_agent(user_agent)
        
        LoginAttempt.objects.create(
            username=user.username,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_info['device_type'],
            browser=device_info['browser'],
            os=device_info['os'],
            event_type='logout',
            is_successful=True,
            risk_level='low',
            details=f"Выход пользователя с устройства: {device_info['browser']} на {device_info['os']}"
        )
        
        logger.info(f"User {user.username} logged out from {ip_address}")
    except Exception as e:
        logger.error(f"Error logging logout: {e}")


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """Логирование неудачного входа через сигнал с созданием блокировок"""
    try:
        username = credentials.get('username', 'Unknown')
        ip_address = _get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Определяем информацию об устройстве
        device_info = _parse_user_agent(user_agent)
        
        # Проверяем на подозрительную активность
        is_suspicious, risk_level, suspicious_reason = _check_suspicious_activity(
            username, ip_address, False, request, None
        )
        
        logger.warning(f"Failed login attempt: {username} from {ip_address}")
        
        # Увеличиваем счетчик неудачных попыток и блокируем при необходимости
        is_blocked, block = IPBlock.increment_failed_attempts(ip_address, user_agent)
        
        if is_blocked:
            logger.warning(f"IP {ip_address} blocked due to too many failed attempts")
            suspicious_reason = 'Блокировка IP из-за множества неудачных попыток'
            is_suspicious = True
            risk_level = 'high'
        
        # Создаем запись о неудачной попытке
        LoginAttempt.objects.create(
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_info['device_type'],
            browser=device_info['browser'],
            os=device_info['os'],
            event_type='failed_login',
            is_successful=False,
            is_suspicious=is_suspicious,
            risk_level=risk_level,
            reason=suspicious_reason if is_suspicious else '',
            details=f"Неудачная попытка входа с устройства: {device_info['browser']} на {device_info['os']}"
        )
    except Exception as e:
        logger.error(f"Error logging failed login: {e}")


def _parse_user_agent(user_agent):
    """
    Парсинг User-Agent для определения устройства, браузера и ОС
    """
    device_type = 'desktop'
    browser = 'Unknown'
    os = 'Unknown'
    
    ua_lower = user_agent.lower()
    
    # Определение типа устройства
    if 'mobile' in ua_lower or 'android' in ua_lower:
        device_type = 'mobile'
    elif 'tablet' in ua_lower or 'ipad' in ua_lower:
        device_type = 'tablet'
    elif 'iphone' in ua_lower:
        device_type = 'mobile'
    
    # Определение браузера
    if 'chrome' in ua_lower and 'edge' not in ua_lower:
        browser = 'Chrome'
    elif 'firefox' in ua_lower:
        browser = 'Firefox'
    elif 'safari' in ua_lower and 'chrome' not in ua_lower:
        browser = 'Safari'
    elif 'edge' in ua_lower:
        browser = 'Edge'
    elif 'opera' in ua_lower:
        browser = 'Opera'
    
    # Определение ОС
    if 'windows' in ua_lower:
        os = 'Windows'
    elif 'mac os x' in ua_lower or 'macos' in ua_lower:
        os = 'macOS'
    elif 'linux' in ua_lower:
        os = 'Linux'
    elif 'android' in ua_lower:
        os = 'Android'
    elif 'ios' in ua_lower or 'iphone' in ua_lower or 'ipad' in ua_lower:
        os = 'iOS'
    
    return {
        'device_type': device_type,
        'browser': browser,
        'os': os
    }


def _check_suspicious_activity(username, ip_address, success, request, user):
    """
    Проверка на подозрительную активность
    """
    is_suspicious = False
    risk_level = 'low'
    reason = ''
    
    # Проверка на попытку входа с неизвестного IP для пользователя
    if success and user:
        previous_logins = LoginAttempt.objects.filter(
            user=user,
            is_successful=True
        ).exclude(ip_address=ip_address).count()
        
        if previous_logins > 0:
            # Пользователь ранее входил с других IP
            recent_different_ips = LoginAttempt.objects.filter(
                user=user,
                is_successful=True,
                timestamp__gte=timezone.now() - timezone.timedelta(hours=24)
            ).values('ip_address').distinct().count()
            
            if recent_different_ips >= 3:
                is_suspicious = True
                risk_level = 'medium'
                reason = 'Множественные входы с разных IP за короткий период'
    
    # Проверка на подозрительный User-Agent
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    if not user_agent or len(user_agent) < 10:
        is_suspicious = True
        risk_level = 'medium'
        reason = 'Пустой или подозрительный User-Agent'
    
    # Проверка на ботов
    bot_patterns = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget']
    ua_lower = user_agent.lower()
    for pattern in bot_patterns:
        if pattern in ua_lower:
            is_suspicious = True
            risk_level = 'high'
            reason = 'Обнаружен бот или автоматический скрипт'
            break
    
    return is_suspicious, risk_level, reason


def _get_client_ip(request):
    """
    Получение IP адреса клиента
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    return ip or '0.0.0.0'
