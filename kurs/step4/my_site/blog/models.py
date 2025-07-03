from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from django.db.models import Avg

class Post(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    def approved_comments(self):
        """Возвращает одобренные комментарии к посту"""
        return self.comments.filter(approved_comment=True)

    def average_rating(self):
        """Вычисляет средний рейтинг поста"""
        return self.ratings.aggregate(Avg('value'))['value__avg'] or 0

    def user_rating(self, user):
        """Возвращает оценку пользователя для поста"""
        try:
            return self.ratings.get(user=user).value
        except self.ratings.model.DoesNotExist:
            return 0

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk': self.pk})

class Comment(models.Model):
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.author.username}: {self.text[:50]}"

class Rating(models.Model):
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    value = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    created_date = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('post', 'user')  # Один пользователь - одна оценка на пост
        verbose_name = 'Оценка'
        verbose_name_plural = 'Оценки'

    def __str__(self):
        return f"{self.user.username} оценил {self.post.title} на {self.value}"