from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from posts.models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):
    def setUp(self):
        # Устанавливаем данные для тестирования
        # Создаём экземпляр клиента. Он неавторизован.
        self.guest_client = Client()

    def test_homepage(self):
        """Проверка главной страницы."""
        # Отправляем запрос через client,
        # созданный в setUp()
        response = self.guest_client.get('/')
        # Утверждаем, что для прохождения теста
        # код должен быть равен 200 (HTTPStatus.OK)
        self.assertEqual(response.status_code, HTTPStatus.OK)


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.not_author = User.objects.create_user(username='NotAuthor')
        cls.popular_author = User.objects.create_user(username='PopularAuthor')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст поста',
        )
        cls.popular_author_post = Post.objects.create(
            author=cls.popular_author,
            text='Тестовый текст популярного автора',
        )
        cls.guest_urls = {
            '/': 'posts/index.html',
            '/group/test_slug/': 'posts/group_list.html',
            '/profile/HasNoName/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html'
        }
        cls.authorized_urls = {
            '/create/': 'posts/create_post.html',
        }
        cls.comment_urls = {
            '/posts/1/comment/': 'posts/post_detail.html'
        }
        cls.copyrighted_urls = {
            '/posts/1/edit/': 'posts/create_post.html'
        }
        cls.stop_piracy_redirect = '/posts/1/'
        cls.follow_urls_redirect = {
            '/profile/PopularAuthor/follow/':
            '/auth/login/?next=/profile/PopularAuthor/follow/',
            '/profile/PopularAuthor/unfollow/':
            '/auth/login/?next=/profile/PopularAuthor/unfollow/'
        }

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованный клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user)
        # Создаем авторизованный клиент, но не автор
        self.authorized_not_author = Client()
        # Авторизуем пользователя - не автора
        self.authorized_not_author.force_login(self.not_author)
        cache.clear()

    def test_guest_urls_exist_at_desired_location(self):
        """Проверка страниц, доступных любому пользователю."""
        for url in self.guest_urls.keys():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_authorized_urls_exist_at_desired_location(self):
        """Проверка страниц, доступных авторизованному пользователю."""
        for url in self.authorized_urls.keys():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_copyrighted_urls_exist_at_desired_location(self):
        """Проверка страниц, доступных правообладателю."""
        for url in self.copyrighted_urls.keys():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        all_urls = {
            **self.guest_urls,
            **self.authorized_urls,
            **self.copyrighted_urls
        }
        for address, template in all_urls.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template or None)

    def test_unexisting_page(self):
        """URL-адрес несуществующей страницы возвращает ошибку 404
        (HTTPStatus.NOT_FOUND).
        """
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(
            response.status_code,
            HTTPStatus.NOT_FOUND
        )
        self.assertTemplateUsed(
            response, 'core/404.html'
        )

    def test_redirect_create_post(self):
        """URL-адрес создания поста перенаправляет
        неавторизованного пользователя авторизоваться.
        """
        for url in self.authorized_urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_redirect_comment_post(self):
        """URL-адрес комментирования поста перенаправляет
        неавторизованного пользователя авторизоваться.
        """
        for url in self.comment_urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertRedirects(
                    response,
                    '/auth/login/?next=/posts/1/comment/'
                )

    def test_redirect_edit_post(self):
        """URL-адрес редактирования поста
        перенаправляет НЕ автора на страницу поста.
        """
        for url in self.copyrighted_urls:
            with self.subTest(url=url):
                response = self.authorized_not_author.get(url)
                self.assertRedirects(response, self.stop_piracy_redirect)

    def test_redirect_follow_author(self):
        """URL-адрес подписки/отписки перенаправляет
        неавторизованного пользователя авторизоваться.
        """
        for url, redirect_path in self.follow_urls_redirect.items():
            with self.subTest(url=url, redirect_path=redirect_path):
                response = self.guest_client.get(url)
                self.assertRedirects(
                    response,
                    redirect_path
                )
