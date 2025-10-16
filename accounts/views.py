# accounts/views.py

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import CustomUser, Follow
from .serializers import UserRegisterSerializer, UserSerializer, FollowSerializer
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView # APIViewをインポート
from rest_framework import status
from rest_framework.response import Response
from rest_framework import permissions

# ユーザー登録API
class UserRegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer
    # 登録は誰でも可能
    permission_classes = [permissions.AllowAny] 
    
    def perform_create(self, serializer):
        # カスタムユーザーモデルのcreate_userでハッシュ化される
        serializer.save()

# 自分のユーザー情報表示/更新API
class UserDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    # 認証済みユーザーのみアクセス可能
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # リクエストしているユーザー自身を返す
        return self.request.user

# ユーザー一覧表示API
class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    # 読み取りは許可、書き込みは認証が必要
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# フォロー/アンフォローAPI
class FollowToggleView(APIView):
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # POSTリクエストでフォローを行う
    def post(self, request, user_id):
        following_user_id = self.kwargs['user_id']
        following_user = get_object_or_404(CustomUser, pk=user_id)
        follower_user = request.user
        
        # 自分で自分をフォローできないようにするバリデーション
        if follower_user == following_user:
            return Response({"detail": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        # 既にフォローしているかチェック
        if Follow.objects.filter(follower=follower_user, following=following_user).exists():
            return Response({"detail": "Already following."}, status=status.HTTP_400_BAD_REQUEST)

        # フォロー作成
        Follow.objects.create(follower=follower_user, following=following_user)
        return Response({"detail": "Followed successfully."}, status=status.HTTP_201_CREATED)

    # DELETEリクエストでアンフォローを行う
    def delete(self, request, user_id):
        following_user_id = self.kwargs['user_id']
        following_user = get_object_or_404(CustomUser, pk=user_id)
        follower_user = request.user
        
        # フォローレコードの取得と削除
        follow_instance = get_object_or_404(Follow, follower=follower_user, following=following_user)
        follow_instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# フォローしているユーザー一覧API
class FollowingListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # リクエストユーザーがフォローしているユーザー（following）のリストを返す
        return CustomUser.objects.filter(follower_set__follower=self.request.user)