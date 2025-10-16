# accounts/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ユーザー登録
    path('register/', views.UserRegisterView.as_view(), name='user_register'),
    # 自分のユーザー情報表示・更新
    path('me/', views.UserDetailView.as_view(), name='user_detail'),
    # ユーザー一覧
    path('users/', views.UserListView.as_view(), name='user_list'),
    
    # フォロー/アンフォロー (user_id で対象ユーザーを指定)
    path('follow/<int:user_id>/toggle/', views.FollowToggleView.as_view(), name='follow_toggle'),
    # フォローしているユーザー一覧
    path('following/', views.FollowingListView.as_view(), name='following_list'),
]