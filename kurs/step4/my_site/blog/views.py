from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from .forms import CommentForm
from .models import Post, Rating


def home(request):
    context = {
        'posts': Post.objects.all().order_by('-date_posted'),
        'title': 'Главная страница'
    }
    return render(request, 'blog/home.html', context)


class PostListView(ListView):
    model = Post
    template_name = 'blog/home.html'
    context_object_name = 'posts'
    ordering = ['-date_posted']
    paginate_by = 5

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Главная страница'
        context['form'] = CommentForm()
        return context


class UserPostListView(ListView):
    model = Post
    template_name = 'blog/user_posts.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs.get('username'))
        return Post.objects.filter(author=user).order_by('-date_posted')


class PostDetailView(DetailView):
    model = Post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['user_rating'] = self.object.user_rating(self.request.user) if self.request.user.is_authenticated else 0
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['title', 'content']
    template_name = 'blog/post_form.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    fields = ['title', 'content']
    template_name = 'blog/post_form.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = '/'
    template_name = 'blog/post_confirm_delete.html'

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author


@login_required
@require_POST
def rate_post(request):
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
            'total_ratings': post.ratings.count()
        })

    return JsonResponse({'success': False}, status=400)


def about(request):
    return render(request, 'blog/about.html', {'title': 'О клубе Python Bites'})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, 'Комментарий успешно добавлен!')
            return redirect('post-detail', pk=post.id)
    return redirect('post-detail', pk=post.id)