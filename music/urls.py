from django.urls import path
from . import views

# この urlpatterns リストが必須です
urlpatterns = [
    # POST /music/share/
    path('share/', views.ShareCurrentSongView.as_view(), name='music_share'),
    
    # GET /music/feed/
    path('feed/', views.FollowingFeedView.as_view(), name='music_feed'),
]