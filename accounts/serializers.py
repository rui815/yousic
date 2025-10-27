# accounts/serializers.py

from rest_framework import serializers
from .models import CustomUser, Follow
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

# ユーザー登録用シリアライザ
class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True) # パスワードは読み取り不可にする
    token = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CustomUser
        # fieldsに 'token' を追加
        fields = ('id', 'username', 'email', 'password', 'token')

    # パスワードをハッシュ化して保存するためのカスタムcreateメソッド
    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''), # emailはオプションとする
            password=validated_data['password']
        )
        return user
    
    # 'token' フィールドの値を計算して返すメソッド
    def get_token(self, user):
        # ユーザーオブジェクトを受け取り、RefreshTokenとAccessTokenを生成
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

# ユーザー情報表示用シリアライザ
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email') # 必要な情報のみを公開

# ログイン用シリアライザ（トークン認証の場合は不要になることが多いですが、
# ログイン認証情報をビューに渡すために作成します）
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Incorrect Credentials")

# フォロー機能用シリアライザ
class FollowSerializer(serializers.ModelSerializer):
    follower_username = serializers.ReadOnlyField(source='follower.username')
    following_username = serializers.ReadOnlyField(source='following.username')

    class Meta:
        model = Follow
        fields = ('id', 'follower', 'following', 'follower_username', 'following_username', 'created_at')
        read_only_fields = ('follower',) # followerは自動で現在のユーザーにするため

    # 重複フォローを防ぐバリデーション（モデルのunique_togetherでも制御しています）
    def validate(self, data):
        follower = self.context['request'].user
        following = data.get('following')
        
        if follower == following:
            raise serializers.ValidationError("You cannot follow yourself.")

        # 新規作成時のみ重複チェック
        if self.instance is None and Follow.objects.filter(follower=follower, following=following).exists():
            raise serializers.ValidationError("You are already following this user.")
            
        return data

#Spotifyように追記
class CurrentTrackSerializer(serializers.Serializer):
    """
    Spotify APIから返されるトラック情報を簡潔に整形するSerializer。
    """
    is_playing = serializers.BooleanField(read_only=True)
    track_name = serializers.CharField(max_length=255, read_only=True)
    artist_name = serializers.CharField(max_length=255, read_only=True)
    album_image_url = serializers.URLField(read_only=True, required=False)

    def to_representation(self, instance):
        # APIの返り値から必要な情報を抽出・整形
        
        # エラーメッセージが含まれている場合
        if instance and instance.get('error'):
            return instance
            
        # 現在再生中の曲 (キー: 'item')
        if instance and instance.get('item'):
            track = instance['item']
            return {
                "is_playing": instance.get('is_playing', True),
                "track_name": track.get('name'),
                "artist_name": track.get('artists')[0].get('name') if track.get('artists') else 'N/A',
                "album_image_url": track.get('album', {}).get('images', [{}])[0].get('url') if track.get('album', {}).get('images') else None,
            }
        
        # 直近再生した曲 (キー: 'items'、リストの最初の要素)
        elif instance and instance.get('items') and len(instance['items']) > 0:
            item = instance['items'][0]
            track = item.get('track', {})
            return {
                "is_playing": False, # 直近再生なのでis_playingはFalse
                "track_name": track.get('name'),
                "artist_name": track.get('artists')[0].get('name') if track.get('artists') else 'N/A',
                "album_image_url": track.get('album', {}).get('images', [{}])[0].get('url') if track.get('album', {}).get('images') else None,
            }

        # 曲情報がない場合
        return {
            "is_playing": False,
            "track_name": "N/A",
            "artist_name": "N/A",
            "message": "現在、または直近に再生された曲情報はありません。"
        }