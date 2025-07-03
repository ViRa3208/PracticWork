from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from .models import Profile
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Создает профиль пользователя при создании нового пользователя.
    Обрабатывает возможные исключения при создании профиля.
    """
    if created:
        try:
            Profile.objects.create(user=instance)
            logger.info(f"Создан профиль для пользователя {instance.username}")
        except Exception as e:
            logger.error(f"Ошибка при создании профиля для {instance.username}: {str(e)}")
            # Можно добавить дополнительную обработку ошибки

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Сохраняет профиль пользователя при обновлении пользователя.
    Проверяет существование профиля перед сохранением.
    """
    try:
        instance.profile.save()
        logger.debug(f"Профиль пользователя {instance.username} обновлен")
    except ObjectDoesNotExist:
        # Если профиль не существует, создаем его
        Profile.objects.create(user=instance)
        logger.warning(f"Профиль для {instance.username} не существовал, создан новый")
    except Exception as e:
        logger.error(f"Ошибка при сохранении профиля {instance.username}: {str(e)}")