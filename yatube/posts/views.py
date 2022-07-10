from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User
from .utils import paginator


@cache_page(20, key_prefix='index_page')
def index(request):
    post_list = Post.objects.select_related(
        'author', 'group'
    )
    context = paginator(request, post_list)
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.groups.select_related(
        'author', 'group'
    )
    context = {
        'group': group,
    }
    context.update(paginator(request, post_list))
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    total_posts = author.posts.count()
    post_list = author.posts.all()
    if request.user.is_authenticated and Follow.objects.filter(
        author=author,
        user=request.user,
    ).exists():
        following = True
    else:
        following = False
    context = {
        'author': author,
        'total_posts': total_posts,
        'following': following,
    }
    context.update(paginator(request, post_list))
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    total_posts = post.author.posts.count()
    comment_list = Comment.objects.filter(
        post=post
    )
    context = {
        'post': post,
        'total_posts': total_posts,
        'form': form,
        'comment_list': comment_list,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required()
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None)
    if form.is_valid():
        new_post = form.save(commit=False)
        new_post.author = request.user
        new_post.save()
        return redirect('posts:profile', username=new_post.author)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required()
def post_edit(request, post_id):
    post_for_edit = get_object_or_404(Post, pk=post_id)
    if post_for_edit.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post_for_edit)
    if form.is_valid():
        post_for_edit = form.save(commit=False)
        post_for_edit.author = request.user
        post_for_edit.save()
        return redirect('posts:post_detail', post_id=post_id)
    return render(
        request,
        'posts/create_post.html',
        {'is_edit': True, 'form': form}
    )


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    context = paginator(request, post_list)
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author_following = get_object_or_404(User, username=username)
    if Follow.objects.filter(
        author=author_following, user=request.user
    ).exists() or request.user == author_following:
        return redirect('posts:profile', username=username)
    Follow.objects.create(user=request.user, author=author_following)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    author_following = get_object_or_404(User, username=username)
    if not Follow.objects.filter(
        author=author_following, user=request.user
    ).exists() or request.user == author_following:
        return redirect('posts:profile', username=username)
    Follow.objects.filter(
        author=author_following,
        user=request.user
    ).delete()
    return redirect('posts:profile', username=username)
