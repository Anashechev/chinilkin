"""
Команда для проверки обновлений безопасности и уязвимостей
"""
from django.core.management.base import BaseCommand
import subprocess
import sys


class Command(BaseCommand):
    help = 'Проверка обновлений безопасности и уязвимостей зависимостей'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Проверка безопасности системы ==='))
        
        # Проверка версии Django
        self.check_django_version()
        
        # Проверка уязвимостей с помощью pip-audit
        self.check_vulnerabilities()
        
        # Проверка безопасности настроек Django
        self.check_django_security()
        
        self.stdout.write(self.style.SUCCESS('=== Проверка завершена ==='))
    
    def check_django_version(self):
        """Проверка актуальности версии Django"""
        self.stdout.write('\n--- Проверка версии Django ---')
        try:
            import django
            current_version = django.get_version()
            self.stdout.write(f'Текущая версия Django: {current_version}')
            
            # Проверка наличия обновлений через pip
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'list', '--outdated', '--format=json'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                import json
                outdated = json.loads(result.stdout)
                for package in outdated:
                    if package['name'] == 'Django':
                        self.stdout.write(
                            self.style.WARNING(
                                f'Доступна новая версия Django: {package["latest_version"]} '
                                f'(текущая: {package["version"]})'
                            )
                        )
                        self.stdout.write('Команда для обновления: pip install --upgrade Django')
                        break
                else:
                    self.stdout.write(self.style.SUCCESS('Django актуален'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка проверки версии Django: {e}'))
    
    def check_vulnerabilities(self):
        """Проверка уязвимостей с помощью pip-audit"""
        self.stdout.write('\n--- Проверка уязвимостей зависимостей ---')
        
        # Проверка наличия pip-audit
        try:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'show', 'pip-audit'],
                capture_output=True,
                check=True
            )
            has_pip_audit = True
        except subprocess.CalledProcessError:
            has_pip_audit = False
        
        if has_pip_audit:
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'audit'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    self.stdout.write(self.style.SUCCESS('Уязвимостей не обнаружено'))
                else:
                    self.stdout.write(self.style.WARNING('Обнаружены уязвимости:'))
                    self.stdout.write(result.stdout)
                    self.stdout.write('\nРекомендации:')
                    self.stdout.write('1. Обновите уязвимые пакеты: pip install --upgrade <package_name>')
                    self.stdout.write('2. Или используйте: pip install --upgrade -r requirements.txt')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Ошибка проверки уязвимостей: {e}'))
        else:
            self.stdout.write(
                self.style.WARNING(
                    'pip-audit не установлен. Установите его для проверки уязвимостей:'
                )
            )
            self.stdout.write('pip install pip-audit')
    
    def check_django_security(self):
        """Проверка настроек безопасности Django"""
        self.stdout.write('\n--- Проверка настроек безопасности Django ---')
        
        from django.conf import settings
        
        checks = []
        
        # Проверка DEBUG
        if settings.DEBUG:
            checks.append(('DEBUG=True', 'Отключите DEBUG в production'))
        
        # Проверка SECRET_KEY
        if 'django-insecure' in settings.SECRET_KEY or settings.SECRET_KEY == '':
            checks.append(('Небезопасный SECRET_KEY', 'Используйте надежный секретный ключ'))
        
        # Проверка ALLOWED_HOSTS
        if '*' in settings.ALLOWED_HOSTS and settings.DEBUG:
            checks.append(('ALLOWED_HOSTS=["*"]', 'Укажите конкретные домены в production'))
        
        # Проверка настроек безопасности
        security_settings = {
            'SECURE_BROWSER_XSS_FILTER': True,
            'SECURE_CONTENT_TYPE_NOSNIFF': True,
            'X_FRAME_OPTIONS': 'DENY',
            'SESSION_COOKIE_HTTPONLY': True,
            'CSRF_COOKIE_HTTPONLY': True,
        }
        
        for setting, expected in security_settings.items():
            value = getattr(settings, setting, None)
            if value is None:
                checks.append((f'{setting} не настроен', f'Добавьте {setting} в settings.py'))
        
        # Отдельная проверка для HSTS
        hsts_seconds = getattr(settings, 'SECURE_HSTS_SECONDS', None)
        if hsts_seconds is None or hsts_seconds < 31536000:
            checks.append(('SECURE_HSTS_SECONDS не настроен или слишком мал', 'Добавьте SECURE_HSTS_SECONDS = 31536000 в settings.py'))
        
        if checks:
            self.stdout.write(self.style.WARNING('Обнаружены проблемы с настройками безопасности:'))
            for issue, recommendation in checks:
                self.stdout.write(f'  - {issue}')
                self.stdout.write(f'    Рекомендация: {recommendation}')
        else:
            self.stdout.write(self.style.SUCCESS('Настройки безопасности настроены корректно'))
