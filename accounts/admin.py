from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Follow

# Django管理画面でCustomUserをカスタマイズ
class CustomUserAdmin(UserAdmin):
    # UserAdminのフィールドセットをコピー
    fieldsets = list(UserAdmin.fieldsets)
    
    # ★「Spotify 認証情報」というセクションを追加
    fieldsets.append(
        ('Spotify 認証情報', {
            'fields': ('spotify_access_token', 'spotify_refresh_token', 'spotify_token_expires_at'),
        })
    )
    
    # リスト表示にも追加（任意）
    list_display = ('username', 'email', 'is_staff', 'spotify_access_token')

# --- ★ 修正箇所 ---
# CustomUser が既に登録されているか確認してから unregister を試みる
if admin.site.is_registered(CustomUser):
    admin.site.unregister(CustomUser)

# 修正した CustomUserAdmin で CustomUser を登録
admin.site.register(CustomUser, CustomUserAdmin)
# --- 修正ここまで ---

# Followモデルを管理サイトに登録
admin.site.register(Follow)