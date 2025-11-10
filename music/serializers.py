from rest_framework import serializers
from .models import SongShare
# 既存のaccountsアプリからUserSerializerをインポートして、ユーザー情報をネスト表示する
from accounts.serializers import UserSerializer

class SongShareSerializer(serializers.ModelSerializer):
    # userフィールドをネストして表示
    # 投稿したユーザーのIDだけでなく、ユーザー名なども一緒に返せるようにする
    user = UserSerializer(read_only=True)

    class Meta:
        model = SongShare
        fields = (
            'id', 
            'user', 
            'spotify_track_id', 
            'track_name', 
            'artist_name', 
            'album_cover_url', 
            'shared_at'
        )
        read_only_fields = ('user',) # userはAPIリクエストからではなく、認証情報から自動で設定