import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import CommentForm, PostForm
from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.authorized_client = Client()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client.force_login(self.user)

    def post_form_check(self, form, checking_post):
        context = {
            self.user.username: checking_post.author.username,
            form['text']: checking_post.text,
            form['group']: checking_post.group.pk,
            'posts/' + form['image'].name: checking_post.image.name,
            form['image'].size: checking_post.image.size,
        }
        for expected_context, created_context in context.items():
            with self.subTest(expected_context=expected_context):
                self.assertEqual(expected_context, created_context)

    def test_post_create(self):
        """Валидная форма создает пост в Posts."""
        small_gif_for_create = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded_for_create = SimpleUploadedFile(
            name='small_gif_for_create.gif',
            content=small_gif_for_create,
            content_type='image/gif'
        )
        posts_count = Post.objects.count()
        form_create_data = {
            'text': 'Тестовый текст',
            'group': self.group.pk,
            'image': uploaded_for_create,
        }
        form = PostForm(data=form_create_data)
        self.assertTrue(form.is_valid())
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=form_create_data, follow=True
        )
        self.assertRedirects(
            response, reverse('posts:profile', args=[self.user.username])
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        created_post = Post.objects.first()
        self.post_form_check(form_create_data, created_post)

    def test_post_edit(self):
        """Валидная форма редактирует пост в Posts."""
        small_gif_for_edit = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded_for_edit = SimpleUploadedFile(
            name='small_gif_for_edit.gif',
            content=small_gif_for_edit,
            content_type='image/gif'
        )
        post_for_edit = Post.objects.create(
            author=self.user,
            text='Тестовый текст поста для редактирования',
            group=self.group,
            image=uploaded_for_edit
        )
        small_gif_for_change = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded_for_change = SimpleUploadedFile(
            name='small_gif_for_change.gif',
            content=small_gif_for_change,
            content_type='image/gif'
        )
        posts_count = Post.objects.count()
        form_edit_data = {
            'text': 'Тестовый текст поста для редактирования изменён',
            'group': post_for_edit.group.pk,
            'image': uploaded_for_change,
        }
        self.assertTrue(PostForm(data=form_edit_data).is_valid())
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=[post_for_edit.pk]),
            data=form_edit_data, follow=True
        )
        self.assertRedirects(
            response, reverse('posts:post_detail', args=[post_for_edit.pk])
        )
        self.assertEqual(Post.objects.count(), posts_count)
        edited_post = Post.objects.get(pk=post_for_edit.pk)
        self.post_form_check(form_edit_data, edited_post)


class CommentFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.post_for_comment = Post.objects.create(
            author=cls.user,
            text='Тестовый текст поста для комментирования',
        )
        cls.form = CommentForm()
        cls.authorized_client = Client()

    def setUp(self):
        self.authorized_client.force_login(self.user)

    def test_post_comment(self):
        """Валидная форма создает комментарий к посту."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый текст комментария',
        }
        form = CommentForm(data=form_data)
        self.assertTrue(form.is_valid())
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                args=[self.post_for_comment.pk]
            ),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=[self.post_for_comment.pk])
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        created_comment = Comment.objects.get(
            author=self.user,
            text=form_data['text'],
        )
        self.assertEqual(form_data['text'], created_comment.text)
