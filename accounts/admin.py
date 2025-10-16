# accounts/admin.py

from django.contrib import admin
from .models import CustomUser, Follow

# CustomUserモデルを管理サイトに登録
# ユーザーが多い場合や表示を細かく制御したい場合は専用のAdminクラスを定義しますが、
# ここでは一旦シンプルに登録します。
admin.site.register(CustomUser)

# Followモデルを管理サイトに登録
admin.site.register(Follow)