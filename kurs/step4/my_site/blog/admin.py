from django.contrib import admin
from .models import Post, Comment

admin.site.register(Post)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('text', 'author', 'post', 'created_date')
    list_filter = ('created_date', 'author')
    search_fields = ('text', 'author__username')
    date_hierarchy = 'created_date'