from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from .models import Profile
from blog.models import Post, Rating  # Импорт моделей из приложения blog


def register(request):
    """Обработка регистрации новых пользователей"""
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, 'Ваш аккаунт создан: можно войти на сайт.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    """Обновление профиля пользователя"""
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES,
                                   instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Ваш профиль успешно обновлен!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'users/profile.html', context)


@login_required
@require_POST
def rate_post(request):
    """Обработка оценки поста (AJAX)"""
    post_id = request.POST.get('post_id')
    value = int(request.POST.get('value', 0))

    if 1 <= value <= 5:
        post = get_object_or_404(Post, id=post_id)
        Rating.objects.update_or_create(
            post=post,
            user=request.user,
            defaults={'value': value}
        )
        return JsonResponse({
            'success': True,
            'average_rating': post.average_rating(),
            'user_rating': value,
            'total_ratings': post.ratings.count()  # Добавлено количество оценок
        })

    return JsonResponse({'success': False}, status=400)