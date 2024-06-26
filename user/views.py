import os.path

from django import views
from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse

from readingforum.settings import MEDIA_ROOT, MEDIA_URL
from user.forms import *
from user.service.userinfo_service import *
from user.service.verification_service import *
from utils.file_utils import save_file
from utils.view_decorator import AuthRequired

# Create your views here.
userinfo_service = UserInfoService()
verification_service = VerificationService()


class LoginView(views.View):

    def get(self, request):
        form = LoginForm()
        return render(request, 'user/login.html', {'form': form})

    def post(self, request: WSGIRequest):
        form = LoginForm(request.POST)
        if form.is_valid():
            request.session['username'] = form.cleaned_data['username']
            user = userinfo_service.find_userinfo_by_username(
                form.cleaned_data['username'],
                "admin", "avatar_url"
            )
            request.session['user_id'] = str(user.get("_id"))
            request.session['avatar_url'] = user.get("avatar_url")
            if user.get("admin"):
                request.session['is_admin'] = True
            return redirect(request.POST.get("next", "home"))
        return render(request, 'user/login.html', {'form': form})


class RegisterView(views.View):

    def get(self, request):
        form = RegisterForm()
        return render(request, "user/register.html", {"form": form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user_id = userinfo_service.create_user(
                form.cleaned_data['username'],
                form.cleaned_data['password'],
                form.cleaned_data['email']
            ).inserted_id
            verification_service.delete_verification_code(form.cleaned_data['email'])
            request.session['username'] = form.cleaned_data['username']
            request.session['user_id'] = str(user_id)
            return redirect(request.POST.get("next", "home"))
        return render(request, "user/register.html", {"form": form})


class VerifyView(views.View):

    def get(self, request):
        pass

    def post(self, request):
        email_address = request.POST.get("email")  # 邮箱地址
        email_form = EmailForm(data={'email': email_address, 'page': request.POST.get("page")})  # 以键值对的形式直接建立email表单
        if email_form.is_valid():
            email_address = email_form.cleaned_data['email']  # 验证
            verification_service.send_verification_email(email_address)
            request.session['email'] = email_address
        return JsonResponse(data={"errors": email_form.errors})  # 直接把错误信息到ajax的success函数


@AuthRequired.login_required()
def logout(request: WSGIRequest):
    """注销"""
    request.session.clear()  # 删除session数据
    return redirect("home")


@AuthRequired.login_required()
def reset_password_verify(request):
    """重置密码的验证"""
    if request.method == 'GET':
        form = VerifyForm()
        return render(request, "user/reset_password_verify.html", {"form": form})

    form = VerifyForm(request.POST)
    if form.is_valid():
        # 删除数据库存储的验证码
        verification_service.delete_verification_code(form.cleaned_data['email'])
        return redirect(reverse("reset"))
    return render(request, "user/reset_password_verify.html", {"form": form})


@AuthRequired.login_required()
def reset_password(request):
    """重置密码"""
    if request.method == 'GET':
        form = PasswordForm()
        return render(request, "user/reset_password.html", {"form": form})

    form = PasswordForm(request.POST)
    if form.is_valid():
        userinfo_service.update_password(request.session.get("email"), form.cleaned_data.get("password"))
        request.session.clear()
        return redirect(reverse("login"))
    return render(request, "user/reset_password.html", {"form": form})


@AuthRequired.login_required()
def userinfo(request, username):
    user = userinfo_service.find_userinfo_by_username(username, "username", "avatar_url", "introduction")
    email = userinfo_service.get_email(request.session.get('username'))
    register_time = userinfo_service.get_register_time(request.session.get('username'))
    posts_num = userinfo_service.get_posts_num(username)
    comments_num = userinfo_service.get_comments_num(username)
    replies_num = userinfo_service.get_replies_num(username)
    context = {
        "email": email,
        "register_time": register_time,
        "posts_num": posts_num,
        "comments_num": comments_num,
        "replies_num": replies_num
    }
    context.update(user)
    if username != request.session.get("username"):
        del context['email']
    return render(request, 'user/userinfo.html', context)


@AuthRequired.login_required()
def profile(request):
    """编辑用户信息，GET方法，下面的两个函数都是用来验证的，都是POST"""
    edit_avatar_form = AvatarUploadForm()  # 上传头像表单
    userinfo_form = UserInfoForm()  # 用户信息表单
    fields_name = list(userinfo_form.fields.keys())  # 获取表单字段名
    # 设置表单初始值
    userinfo_form.initial = userinfo_service.find_userinfo_by_username(request.session.get('username'), *fields_name)
    addresses = userinfo_service.find_userinfo_by_username(request.session.get('username'), 'addresses').get("addresses")
    return render(request, 'user/userinfo_edit.html',
                  {"edit_avatar_form": edit_avatar_form, "userinfo_form": userinfo_form, "addresses": addresses, "avatar_url": request.session.get('avatar_url')})


def profile_other(request, username):
    """其他用户个人信息"""
    # 获取用户信息
    user = userinfo_service.find_userinfo_by_username(
        username,
        "username", "full_name", "birthday", "introduction", "avatar_url"
    )

    # 初始化用户信息表单
    userinfo_form = UserInfoForm(initial={
        "full_name": user.get("full_name"),
        "birthday": user.get("birthday"),
        "introduction": user.get("introduction")
    })

    return render(request, 'user/userinfo_no_edit_other_user.html', {"userinfo": user, "userinfo_form": userinfo_form, "avatar_url": user.get("avatar_url")})


@AuthRequired.login_required()
def edit_avatar(request):
    """编辑头像"""
    form = AvatarUploadForm(request.POST, request.FILES)
    if form.is_valid():
        avatar = form.cleaned_data['avatar']
        url_path = save_file(avatar, "userinfo/avatar", request.session.get("username"))
        userinfo_service.update_avatar_url(request.session.get("username"), url_path)  # 保存url路径
        # 设置session
        request.session['avatar_url'] = userinfo_service.find_userinfo_by_username(
            request.session.get("username"),
            'avatar_url'
        ).get("avatar_url")

    # userinfo表单
    userinfo_form = UserInfoForm()
    fields_name = list(userinfo_form.fields.keys())
    userinfo_form = UserInfoForm(
        initial=userinfo_service.find_userinfo_by_username(
            request.session.get("username"),
            *fields_name
        )
    )

    # 地址
    addresses = userinfo_service.find_userinfo_by_username(request.session.get('username'), 'addresses').get(
        'addresses')
    return render(request, "user/userinfo_edit.html",
                  {"edit_avatar_form": form, "userinfo_form": userinfo_form, "addresses": addresses})


@AuthRequired.login_required()
def edit_userinfo(request):
    """编辑用户信息"""
    data = request.POST
    form = UserInfoForm(data)
    if form.is_valid():
        userinfo_service.update_user_info(request.session.get("username"), **form.cleaned_data)
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "errors": form.errors})


@AuthRequired.login_required()
def save_addresses(request):
    """保存地址"""
    addresses = request.POST.getlist("addresses[]")
    if userinfo_service.update_user_info(request.session.get("username"), addresses=addresses):
        return JsonResponse({"success": True})
    else:
        return JsonResponse({"success": False})


def is_login(request):
    """是否已登录"""
    username = request.session.get("username")
    is_login = True if username else False
    return JsonResponse({"is_login": is_login})


class PostMessageListView(views.View):
    def get(self, request):
        message_type_count = userinfo_service.count_message_type(request.session.get("user_id"))
        message_type_count["post"] = message_type_count.get("post", 0)
        message_type_count["reply"] = message_type_count.get("reply", 0) + message_type_count.get("reply_reply", 0)

        message_post_count = userinfo_service.count_message_post(request.session.get("user_id"))
        # print(message_type_count)
        # print(message_post_count)

        return render(request, "user/message.html", {"message_type_count": message_type_count, "message_post_count": message_post_count})

    def post(self, request):
        pass


class ReplyMessageListView(views.View):
    def get(self, request):
        message_type_count = userinfo_service.count_message_type(request.session.get("user_id"))
        message_type_count["post"] = message_type_count.get("post", 0)
        message_type_count["reply"] = message_type_count.get("reply", 0) + message_type_count.get("reply_reply", 0)

        message_reply_count = userinfo_service.count_message_reply(request.session.get("user_id"))
        message_reply_reply_count = userinfo_service.count_message_reply_reply(request.session.get("user_id"))
        # print(message_type_count)
        # print(message_reply_count)
        # print(message_reply_reply_count)
        context = {
            "message_type_count": message_type_count,
            "message_reply_count": message_reply_count,
            "message_reply_reply_count": message_reply_reply_count
        }
        return render(request, 'user/message.html', context)

    def post(self, request):
        pass


class MessageClearView(views.View):
    def get(self, request):
        for type_ in [1, 2, 3]:
            userinfo_service.update_message_viewed_status(request.session.get("user_id"), type_)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    def post(self, request):
        pass
