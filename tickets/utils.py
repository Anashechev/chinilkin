from .models import Notification
from cryptography.fernet import Fernet
from django.conf import settings
import base64

def send_notification(recipient, notification_type, title, message, ticket=None):
    """
    Send a notification to a user.
    
    Args:
        recipient: User object to receive the notification
        notification_type: Type of notification (ticket_status, ticket_assigned, system)
        title: Title of the notification
        message: Message content
        ticket: Optional ticket object related to the notification
    """
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        ticket=ticket
    )
    return notification

def send_ticket_status_notification(ticket, new_status, changed_by):
    """
    Send a notification when a ticket status changes.
    
    Args:
        ticket: Ticket object
        new_status: New status of the ticket
        changed_by: User who changed the status
    """
    title = f"Заявка #{ticket.id} - Статус изменен"
    message = f"Статус вашей заявки '{ticket.title}' был изменен на '{new_status.name}' пользователем {changed_by.full_name}."
    
    return send_notification(
        recipient=ticket.client,
        notification_type='ticket_status',
        title=title,
        message=message,
        ticket=ticket
    )

def send_ticket_assigned_notification(ticket, assignee, assigned_by):
    """
    Send a notification when a ticket is assigned to a worker.
    
    Args:
        ticket: Ticket object
        assignee: User assigned to the ticket
        assigned_by: User who assigned the ticket
    """
    title = f"Заявка #{ticket.id} - Назначена"
    message = f"Вы были назначены на заявку '#{ticket.id}: {ticket.title}' пользователем {assigned_by.full_name}."
    
    return send_notification(
        recipient=assignee,
        notification_type='ticket_assigned',
        title=title,
        message=message,
        ticket=ticket
    )


class DataEncryption:
    """Класс для шифрования и расшифрования данных с использованием Fernet"""
    
    def __init__(self):
        """Инициализация шифра с ключом из SECRET_KEY"""
        # Генерация ключа из SECRET_KEY
        key = self._generate_key_from_secret()
        self.cipher = Fernet(key)
    
    def _generate_key_from_secret(self):
        """Генерация 32-байтового ключа из SECRET_KEY"""
        secret = settings.SECRET_KEY.encode()
        # Дополняем или обрезаем до 32 байт
        key = secret[:32].ljust(32, b'0')
        # Кодируем в base64 для Fernet
        return base64.urlsafe_b64encode(key)
    
    def encrypt(self, data):
        """
        Шифрование данных
        
        Args:
            data: Строка или байты для шифрования
            
        Returns:
            Зашифрованные данные в виде строки (base64)
        """
        if isinstance(data, str):
            data = data.encode()
        
        encrypted = self.cipher.encrypt(data)
        return encrypted.decode()
    
    def decrypt(self, encrypted_data):
        """
        Расшифрование данных
        
        Args:
            encrypted_data: Зашифрованные данные (строка или байты)
            
        Returns:
            Расшифрованная строка
        """
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        
        decrypted = self.cipher.decrypt(encrypted_data)
        return decrypted.decode()
    
    def encrypt_dict(self, data_dict, fields_to_encrypt):
        """
        Шифрование указанных полей в словаре
        
        Args:
            data_dict: Словарь с данными
            fields_to_encrypt: Список полей для шифрования
            
        Returns:
            Словарь с зашифрованными полями
        """
        encrypted_dict = data_dict.copy()
        for field in fields_to_encrypt:
            if field in encrypted_dict and encrypted_dict[field]:
                encrypted_dict[field] = self.encrypt(encrypted_dict[field])
        return encrypted_dict
    
    def decrypt_dict(self, encrypted_dict, fields_to_decrypt):
        """
        Расшифрование указанных полей в словаре
        
        Args:
            encrypted_dict: Словарь с зашифрованными данными
            fields_to_decrypt: Список полей для расшифрования
            
        Returns:
            Словарь с расшифрованными полями
        """
        decrypted_dict = encrypted_dict.copy()
        for field in fields_to_decrypt:
            if field in decrypted_dict and decrypted_dict[field]:
                try:
                    decrypted_dict[field] = self.decrypt(decrypted_dict[field])
                except Exception:
                    # Если расшифрование не удалось, оставляем как есть
                    pass
        return decrypted_dict


# Глобальный экземпляр для использования в проекте
encryption = DataEncryption()