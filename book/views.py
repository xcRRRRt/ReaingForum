import pprint

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django import views
from django.views.generic import TemplateView

from book.service.book_service import BookService
from forum.service.post_service import PostService
from user.service.userinfo_service import UserInfoService
from utils.detect_sensitive import Sensitive
from utils.paginator import Paginator, PaginatorFromFunction
from utils.datetime_util import get_datetime_by_objectId

# Create your views here.

book_service = BookService()
userinfo_service = UserInfoService()
post_service = PostService()


class BookHomeView(views.View):
    recommend_book_id = "6667bc36097ceeb2b6576e5e"

    def get(self, request, *args, **kwargs):
        new_books = book_service.find_new_books(0, 4)
        hottest_books = book_service.find_hottest_books(0, 4)
        recommend_book = book_service.find_book_by_id(self.recommend_book_id, "title", "isbn", 'cover', "introduction")
        context = {"new_books": new_books, "hottest_books": hottest_books, "recommend_book": recommend_book}
        return render(request, 'book/book_home.html', context)

    def post(self, request, *args, **kwargs):
        pass


class BookNewListView(views.View):
    paginator = PaginatorFromFunction(book_service.find_new_books, per_page=12)

    def get(self, request, *args, **kwargs):
        page = int(request.GET.get('page', 1))
        self.paginator.page = page
        books = self._process_book(self.paginator.from_function())
        page_info = self.paginator.page_info
        context = {"books": books, "page_info": page_info, "type": "new"}
        return render(request, "book/book_list.html", context)

    def _process_book(self, books):
        for book in books:
            if "label" in book:
                book["label"] = book["label"].split(",")
        return books

    def post(self, request, *args, **kwargs):
        pass


class BookHotListView(views.View):
    paginator = PaginatorFromFunction(book_service.find_hottest_books, per_page=12)

    def get(self, request, *args, **kwargs):
        page = int(request.GET.get('page', 1))
        self.paginator.page = page
        books = self._process_book(self.paginator.from_function())
        page_info = self.paginator.page_info
        context = {"books": books, "page_info": page_info, "type": "hot"}
        return render(request, "book/book_list.html", context)

    def _process_book(self, books):
        for book in books:
            if "label" in book:
                book["label"] = book["label"].split(",")
        return books

    def post(self, request, *args, **kwargs):
        pass


class BookDetailView(views.View):
    """图书详情"""
    comments_num = 7
    comments_asc = False
    post_num = 5

    def get(self, request, book_id):
        book = book_service.find_book_by_id(book_id, 'isbn', 'title', 'cover', 'label', 'comments', 'introduction',
                                            'book_data', 'price', 'status', 'stock', 'posts', map_fields=True)
        comments, posts = [], []
        if book.get("comments"):
            comments = self._get_comments(book.get('comments'))
        if book.get("posts"):
            posts = self._get_posts(book.get("posts"))

        context = {
            "book": book,
            "comments": comments,
            "posts": posts
        }

        if "label" in book:
            labels = book["label"]
            recommend_books = []
            for b in book_service.find_book_by_labels(labels, 0, 3):
                if b.get("id") == str(book.get("id")):
                    continue
                recommend_books.append(b)
            context["recommend_books"] = recommend_books

        return render(request, 'book/book_detail.html', context)

    def post(self, request):
        pass

    def _get_comments(self, _comments: list):
        length = len(_comments)
        comments = []
        while len(comments) < min(length, self.comments_num) and len(_comments) != 0:
            comment = _comments.pop(-1)
            if comment["block"]:
                continue
            user_id = comment.get("user_id")
            user = userinfo_service.find_userinfo_by_id(user_id, "username", "avatar_url")
            comment['username'] = user.get("username")
            comment['avatar_url'] = user.get("avatar_url")
            comment['user_id'] = user_id
            comment['time'] = get_datetime_by_objectId(comment.get("id"))
            comments.append(comment)
        return comments

    def _get_posts(self, post_ids: list):
        length = len(post_ids)
        posts = []
        while len(posts) < min(length, self.post_num) and len(post_ids) != 0:
            post_id = post_ids.pop(-1)
            post = post_service.find_post_by_id(post_id, 'author', 'title', 'content')
            if not post:
                continue
            author = userinfo_service.find_userinfo_by_id(post.get('author'), "username", "avatar_url")
            post['author'] = author.get('username')
            post['author_avatar'] = author.get("avatar_url")
            post['post_time'] = get_datetime_by_objectId(post['_id'])
            post['id'] = post["_id"]
            del post['_id']
            posts.append(post)
        return posts


def book_comment(request, book_id):
    """
    书本详情页发表短评
    """
    comment = request.POST.get('comment')
    user_id = request.session.get('user_id')
    _, has_sensitive = Sensitive.detect_sensitive_words(comment)
    if not has_sensitive and book_service.push_comment(book_id, user_id, comment).acknowledged:
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, 'error': '评论中有敏感词，请修改后重新发布'})


class CommentsListView(views.View):
    """全部评论"""
    per_page = 10
    paginator = PaginatorFromFunction(book_service.find_book_comments, per_page=per_page)
    paginator.sort_by = {"time": -1}

    def get(self, request, book_id):
        """
        request接受参数: limit: int, page: int, time: int {-1, 1}
        """
        limit = int(request.GET.get('limit', self.paginator.per_page))
        page = int(request.GET.get('page', self.paginator.page))
        time_sort = int(request.GET.get('time', self.paginator.sort_by.get('time')))
        self.paginator.page = page
        self.paginator.per_page = limit
        self.paginator.sort_by = {"time": time_sort}
        comments = self.paginator.from_function(book_id=book_id)
        book = book_service.find_book_by_id(book_id, 'isbn', 'title', 'cover', 'label', 'price', 'book_data')
        print(comments)
        return render(request, 'book/comments.html', {"book": book, "comments": comments, 'paginator': self.paginator})

    def post(self, request, book_id):
        pass


class PostsListView(TemplateView):
    template_name = 'book/posts.html'
    paginator = PaginatorFromFunction(post_service.find_book_posts, per_page=10)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.book_id = kwargs.get('book_id')
        self.book = book_service.find_book_by_id(self.book_id, 'isbn', 'title', 'cover', 'posts', 'price', 'book_data')
        page = int(request.GET.get('page', 1))
        asc = int(request.GET.get('asc', -1))
        sort = request.GET.get('sort', "hot")
        if sort not in ['time', 'hot']:
            sort = 'hot'
        if asc not in [1, -1]:
            asc = -1
        print(asc)

        self.paginator.page = page
        self.paginator.clear_sort()
        self.paginator.sort_by = {sort: asc}
        print(self.paginator.sort_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        posts = self.paginator.from_function(post_ids=self.book.get("posts"))
        context['book'] = self.book
        context['posts'] = posts
        context['paginator'] = self.paginator
        return context
