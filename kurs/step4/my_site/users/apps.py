from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        # Импортируем сигналы только после полной загрузки приложения
        from . import signals  # Изменено с 'users.signals' на относительный импорт