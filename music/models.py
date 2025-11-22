from django.db import models
from django.conf import settings # settings.AUTH_USER_MODEL を参照するため

# 共有された曲の履歴を保存するモデル
class SongShare(models.Model):
    # settings.AUTH_USER_MODEL を使うと、CustomUserモデルを直接インポートするより安全です
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='song_shares')
    
    # Spotifyから取得する情報
    spotify_track_id = models.CharField(max_length=100, db_index=True) # 検索用にインデックスを貼る
    track_name = models.CharField(max_length=255)
    artist_name = models.CharField(max_length=255)
    album_cover_url = models.URLField(max_length=500, blank=True, null=True)
    
    # 共有された日時
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 新しい投稿が一番上に来るようにデフォルトの順序を指定
        ordering = ['-shared_at']

    def __str__(self):
        return f"{self.user.username} shared {self.track_name}"

class SpotifyAuthState(models.Model):
    """
    Spotify認証のコールバックが戻ってきたときに、
    どのユーザーのリクエストだったかを特定するための一時的なState保存用
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    state = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"State for {self.user.username}"   