import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post

User = get_user_model()

POSTS_QUANTITY = 12
POSTS_PER_PAGE = 10

small_gif = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewsAndPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.wrong_group = Group.objects.create(
            title='Неверная группа',
            slug='wrong_slug',
            description='Группа, в которую не должен попасть пост',
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        for i in range(POSTS_QUANTITY):
            cls.post = Post.objects.create(
                author=cls.user,
                text='Тестовый текст поста',
                group=cls.group,
                image=cls.uploaded,
            )
        cls.guest_client = Client()
        cls.index = (
            'posts:index',
            None,
            'posts/index.html'
        )
        cls.group_list = (
            'posts:group_list',
            [cls.group.slug],
            'posts/group_list.html'
        )
        cls.profile = (
            'posts:profile',
            [cls.user.username],
            'posts/profile.html'
        )
        cls.post_detail = (
            'posts:post_detail',
            [cls.post.pk],
            'posts/post_detail.html'
        )
        cls.post_edit = (
            'posts:post_edit',
            [cls.post.pk],
            'posts/create_post.html'
        )
        cls.post_create = (
            'posts:post_create',
            None,
            'posts/create_post.html'
        )
        cls.namespace_names = (
            cls.index,
            cls.group_list,
            cls.profile,
            cls.post_detail,
            cls.post_edit,
            cls.post_create,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_use_correct_templates(self):
        """Namespace:name использует соответствующий шаблон."""
        for namespace_name, args, template in self.namespace_names:
            with self.subTest(
                namespace_name=namespace_name, args=args, template=template
            ):
                response = self.authorized_client.get(
                    reverse(namespace_name, args=args)
                )
                self.assertTemplateUsed(response, template)

    def post_check(self, post):
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.group.title, self.group.title)
        self.assertEqual(post.author.username, self.user.username)
        self.assertEqual(post.author.posts.count(), POSTS_QUANTITY)
        self.assertEqual(post.image, self.post.image)

    def test_index_group_list_profile_pages_show_correct_context(self):
        """Шаблоны index, group_list, profile работают с верным контекстом."""
        templates_names = (
            self.index,
            self.group_list,
            self.profile,
        )
        for namespace_name, args, template in templates_names:
            response = self.authorized_client.get(
                reverse(namespace_name, args=args)
            )
            post = response.context['page_obj'][0]
            self.post_check(post)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        for namespace_name, args, template in [self.post_detail]:
            response = self.authorized_client.get(
                reverse(namespace_name, args=args)
            )
            post = response.context.get('post')
            self.post_check(post)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        for namespace_name, args, template in [self.post_edit]:
            response = self.authorized_client.get(
                reverse(namespace_name, args=args)
            )
            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.fields.ChoiceField,
            }
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        for namespace_name, args, template in [self.post_create]:
            response = self.authorized_client.get(
                reverse(namespace_name, args=args)
            )
            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.fields.ChoiceField,
            }
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_extra_post_check(self):
        """Дополнительная проверка поста."""
        posts_index_count = Post.objects.count()
        posts_group_count = Post.objects.filter(
            group=Group.objects.get(title=self.group.title)
        ).count()
        posts_wrong_group_count = Post.objects.filter(
            group=Group.objects.get(title=self.wrong_group.title)
        ).count()
        posts_profile_count = Post.objects.filter(
            author=User.objects.get(username=self.user.username)
        ).count()
        self.assertEqual(posts_index_count, POSTS_QUANTITY)
        self.assertEqual(posts_group_count, POSTS_QUANTITY)
        self.assertEqual(posts_wrong_group_count, 0)
        self.assertEqual(posts_profile_count, POSTS_QUANTITY)


class PaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        for i in range(POSTS_QUANTITY):
            cls.post = Post.objects.create(
                author=cls.user,
                text='Тестовый текст поста',
                group=cls.group,
            )
        cls.pages_with_paginator = (
            ('posts:index', None),
            ('posts:group_list', [cls.group.slug]),
            ('posts:profile', [cls.user.username])
        )

    def setUp(self):
        cache.clear()

    def test_first_page_contains_ten_records(self):
        """Первая страница index, group_list, profile содержит 10 записей."""
        for namespace_name, args in self.pages_with_paginator:
            response = self.client.get(reverse(namespace_name, args=args))
            self.assertEqual(len(response.context['page_obj']), POSTS_PER_PAGE)

    def test_second_page_contains_two_records(self):
        """Вторая страница index, group_list, profile содержит 2 записи."""
        for namespace_name, args in self.pages_with_paginator:
            response = self.client.get(
                reverse(namespace_name, args=args) + '?page=2'
            )
            self.assertEqual(
                len(response.context['page_obj']),
                POSTS_QUANTITY - POSTS_PER_PAGE
            )


class CommentTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.post_with_comment = Post.objects.create(
            author=cls.user,
            text='Тестовый текст поста c комментарием'
        )
        cls.post_without_comment = Post.objects.create(
            author=cls.user,
            text='Тестовый текст поста без комментария'
        )
        cls.guest_client = Client()
        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый текст комментария',
            post=cls.post_with_comment
        )

    def test_extra_comment_check(self):
        """Дополнительная проверка комментария."""
        comment_count = Comment.objects.count()
        comment_in_post_with_comment_count = Comment.objects.filter(
            post=self.post_with_comment
        ).count()
        comment_in_post_without_comment_count = Comment.objects.filter(
            post=self.post_without_comment
        ).count()
        self.assertEqual(comment_count, 1)
        self.assertEqual(comment_in_post_with_comment_count, 1)
        self.assertEqual(comment_in_post_without_comment_count, 0)


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст поста для кэша'
        )
        cls.guest_client = Client()

    def setUp(self):
        cache.clear()

    def test_cache_index_check(self):
        """Проверка работы Cache."""
        response_1 = self.guest_client.get(
            reverse('posts:index')
        )
        self.assertTrue(response_1.context['page_obj'].__contains__(self.post))
        cached_index_page = response_1.content
        self.post.delete()
        response_2 = self.guest_client.get(
            reverse('posts:index')
        )
        self.assertEqual(response_2.content, cached_index_page)
        cache.clear()
        response_3 = self.guest_client.get(
            reverse('posts:index')
        )
        self.assertNotEqual(response_3.content, cached_index_page)


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reader = User.objects.create_user(username='Reader')
        cls.watcher = User.objects.create_user(username='Watcher')
        cls.popular_author = User.objects.create_user(username='PopularAuthor')

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.reader)
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                args=[self.popular_author.username]
            )
        )

    def test_follow_and_unfollow_check(self):
        """Проверка возможности оформить подписку и отписаться"""
        self.assertTrue(
            Follow.objects.filter(
                user=self.reader,
                author=self.popular_author,
            ).exists()
        )
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                args=[self.popular_author.username]
            )
        )
        self.assertFalse(
            Follow.objects.filter(
                user=self.reader,
                author=self.popular_author,
            ).exists()
        )

    def test_followers_post_check(self):
        """Проверка размещения поста в ленте подписчика"""
        Post.objects.create(
            author=self.popular_author,
            text='Тестовый текст поста для проверки подписок'
        )
        self.assertEqual(
            Post.objects.filter(author__following__user=self.reader).count(),
            1)
        self.assertEqual(
            Post.objects.filter(author__following__user=self.watcher).count(),
            0)
