from datetime import datetime
from typing import *

from bson import ObjectId
from pymongo.results import InsertOneResult, UpdateResult

from book.service.book_service import BookService
from user.service.userinfo_service import UserInfoService
from utils.db_operation import MongodbOperation
from utils.tokenize import Tokenizer
from utils.datetime_util import get_datetime_by_objectId

userinfo_service = UserInfoService()
book_service = BookService()


class PostService:
    def __init__(self):
        self.db = MongodbOperation('readingforum', 'post')

    def launch_post(self, content: str, title: str, author: str | ObjectId, labels: Optional[list[str]] = None,
                    bound_book: Optional[str | ObjectId] = None) -> Tuple[InsertOneResult, UpdateResult, UpdateResult]:
        """
        发布帖子后，将帖子数据插入post集合中，并将其_id插入到user集合中的posts中
        :param content: 帖子内容
        :param title: 帖子标题
        :param author: 作者
        :param labels: 帖子标签
        :param bound_book: 绑定的书籍
        :return: post集合插入结果，user_info集合posts push结果，book集合posts push结果
        """
        title_tokenized = Tokenizer.tokenize(title)
        content_tokenized = Tokenizer.tokenize(content)

        data = {
            "title": title,
            "title_tokenized": title_tokenized,
            "content": content,
            "content_tokenized": content_tokenized,
            "author": ObjectId(author),
            "bound_book": ObjectId(bound_book) if bound_book else None,
            "labels": labels if labels else None
        }
        # Remove keys with None values
        data = {k: v for k, v in data.items() if v is not None}
        insert_post_res = self.db.post_insert_one(data)
        update_user_res = userinfo_service.add_post(author, post_id=insert_post_res.inserted_id)
        update_book_res = book_service.push_post(bound_book, post_id=insert_post_res.inserted_id)
        return insert_post_res, update_user_res, update_book_res

    def find_post_by_id(self, post_id: str, *required_fields) -> dict[str, Any] | None:
        """
        使用_id寻找帖子指定字段的值
        :param post_id: ObjectId
        :param required_fields: 需要的字段
        :return: 帖子数据
        """
        projection = {field: 1 for field in required_fields}  # 创建投影，仅包含需要的字段
        return self.db.post_find_one({"_id": ObjectId(post_id)}, projection=projection)

    def update_post_likes(self, post_id: str, username: str,
                          click_like: bool, like_act: bool, unlike_act: bool):
        """
        赞/踩帖子，更新帖子的赞/踩，取消赞/踩
        状态：
        1. F F -> T F   纯点赞 push
        2. F F -> F T   纯点踩 push
        3. T F -> F T   赞→踩 set
        4. F T -> T F   踩→赞 set
        5. T F -> F F   取消赞 pull
        6. F T -> F F   取消踩 pull
        :param post_id: 帖子id
        :param username: 用户名
        :param click_like: 点击赞/踩，True赞，False踩
        :param like_act: 点击按钮之前，赞按钮的状态
        :param unlike_act: 点击按钮之前，踩按钮的状态
        :return: 更新是否成功
        """
        _filter, _update = None, None

        if not like_act and not unlike_act and click_like:
            _filter = {"_id": ObjectId(post_id)}
            _update = {"$push": {"likes": {"username": username, "like": True, "timestamp": str(datetime.now())}}}
        elif not like_act and not unlike_act and not click_like:
            _filter = {"_id": ObjectId(post_id)}
            _update = {"$push": {"likes": {"username": username, "like": False, "timestamp": str(datetime.now())}}}
        elif like_act and not unlike_act and not click_like:
            _filter = {"_id": ObjectId(post_id), "likes.username": username}
            _update = {"$set": {"likes.$.like": False, "likes.$.timestamp": str(datetime.now())}}
        elif not like_act and unlike_act and click_like:
            _filter = {"_id": ObjectId(post_id), "likes.username": username}
            _update = {"$set": {"likes.$.like": True, "likes.$.timestamp": str(datetime.now())}}
        elif like_act and not unlike_act and click_like:
            _filter = {"_id": ObjectId(post_id)}
            _update = {"$pull": {"likes": {"username": username}}}
        elif not like_act and unlike_act and not click_like:
            _filter = {"_id": ObjectId(post_id)}
            _update = {"$pull": {"likes": {"username": username}}}

        res = self.db.post_update_one(_filter, _update)
        return res.acknowledged

    def get_post_likes(self, post_id: str) -> dict[str, Any | None]:
        """
        获取帖子点赞/踩
        :param post_id:
        :return: 获取帖子赞和踩的数量
        """
        pipeline = [
            {"$match": {"_id": ObjectId(post_id)}},
            {"$unwind": "$likes"},
            {"$group": {"_id": "$likes.like", "count": {"$sum": 1}}}
        ]
        count = {}
        res = self.db.post_aggregate(pipeline)
        for doc in res:
            count[str(doc.get("_id")).lower()] = doc.get("count")

        return count

    def have_user_liked_post(self, post_id: str, username: str) -> dict[None | str, bool]:
        """
        判断用户是否点赞过帖子
        :param post_id:
        :param username:
        :return: 用户是否点赞过帖子，{}为没点赞/踩，{‘user_post_like',True}为点赞，{'user_post_unlike':True}为点踩
        """
        post = self.db.post_find_one(
            {"_id": ObjectId(post_id), "likes.username": username},
            {"likes.$": 1}
        )
        if post is None:
            return {}
        return {"user_post_like": True} if post.get("likes")[0].get("like") else {"user_post_unlike": True}

    def find_post_by_labels(self, labels: list[str], skip: int, limit: int, sort_by: dict[str, int]) -> List[Mapping[str, Any]]:
        """

        :param labels:
        :param skip:
        :param limit:
        :param sort_by:
        :return:
        """
        filter_ = {"labels": {"$all": labels}}
        cursor = self.db.post_find(filter_)
        if sort_by:
            cursor = cursor.sort(sort_by)
        posts = list(cursor.limit(limit).skip(skip))
        for post in posts:
            post["id"] = str(post["_id"])
            del post["_id"]
        return posts

    def text_search_posts(self, query: str, skip: int = 0, limit: int = 0, sort_by: dict[str, Any] = None) -> List[dict[str, Any]]:
        """

        :param query:
        :param skip:
        :param limit:
        :param sort_by:
        :return:
        """
        query = Tokenizer.tokenize(query)
        if sort_by is None:
            sort_by = {}
        sort_by.update({"score": {"$meta": "textScore"}})
        filter_ = {"$text": {"$search": query}}
        cursor = self.db.post_find(filter_, {"score": {"$meta": "textScore"}, "title_tokenized": 0, "content_tokenized": 0}).sort(sort_by)
        posts = list(cursor.skip(skip).limit(limit))
        for post in posts:
            post["id"] = str(post["_id"])
            del post["_id"]
        return posts

    def find_book_posts(self, book: dict[str, Any], skip: int, limit: int, sort_by: dict[str, Any]) -> List[dict[str, Any]]:
        """
        找到绑定book的帖子
        :param book:
        :param skip:
        :param limit:
        :param sort_by:
        :return:
        """
        if len(book.get("posts", [])) == 0:
            print(1)
            return []
        post_ids = book.get("posts")
        posts = []
        for post_id in post_ids:
            post = self.find_post_by_id(post_id, 'title', 'content', 'author', 'labels')
            author_id = post.get("author")
            author_info = userinfo_service.find_userinfo_by_id(author_id, 'avatar_url', 'username')
            post["author"] = author_info.get('username')
            post['avatar_url'] = author_info.get('avatar_url')
            post['time'] = get_datetime_by_objectId(post['_id'])
            posts.append(post)
        return posts


if __name__ == '__main__':
    post_service = PostService()
    # print(post_service.have_user_liked_post("65f7e2bd9b0a0c39127c1cea", "testuser1"))
    # print(post_service.find_post_by_labels(['测试'], 0, 10, {}))
    print(post_service.text_search_posts("丰乳肥臀", limit=5))
