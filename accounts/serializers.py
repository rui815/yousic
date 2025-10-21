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