from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    # AbstractUserが提供するフィールド（username, email, passwordなど）に加え、
    # 必要に応じて追加のフィールドを定義できます。
    # 例: bio = models.TextField(blank=True)
    pass

    def __str__(self):
        return self.username

class Follow(models.Model):
    # 'follower'が'following'をフォローする
    follower = models.ForeignKey(CustomUser, related_name='following_set', on_delete=models.CASCADE)
    following = models.ForeignKey(CustomUser, related_name='follower_set', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 同じユーザーが同じユーザーを二重にフォローできないようにする
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"